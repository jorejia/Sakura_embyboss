#! /usr/bin/python3
# -*- coding:utf-8 -*-
"""
emby的api操作方法
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from bot import sidecar_url, sidecar_admin_token, emby_public_url, _open, save_config, LOGGER
from bot.sql_helper.sql_emby import sql_get_emby, sql_update_emby, Emby
from bot.sql_helper.sql_favorites import sql_delete_favorites_by_embyid
from bot.func_helper.utils import pwd_create, convert_runtime, cache


def _mask_url(url):
    try:
        split_url = urlsplit(str(url))
        masked_query = []
        for key, value in parse_qsl(split_url.query, keep_blank_values=True):
            if key.lower() in {"api_key", "apikey", "token", "access_token"}:
                value = "***"
            masked_query.append((key, value))
        return urlunsplit(split_url._replace(query=urlencode(masked_query)))
    except Exception:
        return str(url)


def _service_name(url):
    url_text = str(url)
    if sidecar_url and url_text.startswith(sidecar_url.rstrip("/")):
        return "Sidecar"
    if emby_public_url and url_text.startswith(emby_public_url.rstrip("/")):
        return "Emby图片"
    return "HTTP"


def _request_error_message(method, url, timeout, exc):
    return (
        f"【{_service_name(url)}网络】{method} 请求失败，"
        f"url={_mask_url(url)}，timeout={timeout}，"
        f"error={type(exc).__name__}: {exc}"
    )


class LoggedRequests:
    @staticmethod
    def request(method, url, **kwargs):
        timeout = kwargs.get("timeout", "未设置")
        try:
            response = requests.request(method, url, **kwargs)
        except requests.exceptions.Timeout as e:
            LOGGER.error(_request_error_message(method, url, timeout, e) + "。判断：目标服务无响应或网络链路超时")
            raise
        except requests.exceptions.ConnectionError as e:
            LOGGER.error(_request_error_message(method, url, timeout, e) + "。判断：DNS/端口/路由/防火墙/服务未启动/代理链路异常")
            raise
        except requests.exceptions.RequestException as e:
            LOGGER.error(_request_error_message(method, url, timeout, e))
            raise

        if response.status_code >= 400:
            LOGGER.warning(
                f"【{_service_name(url)}网络】{method} 请求返回 HTTP {response.status_code}，"
                f"url={_mask_url(response.url)}，timeout={timeout}，body={response.text[:200]}"
            )
        return response

    @staticmethod
    def get(url=None, **kwargs):
        return LoggedRequests.request("GET", url, **kwargs)

    @staticmethod
    def post(url=None, **kwargs):
        return LoggedRequests.request("POST", url, **kwargs)

    @staticmethod
    def delete(url=None, **kwargs):
        return LoggedRequests.request("DELETE", url, **kwargs)


r = LoggedRequests


class Embyservice:
    """
    账号、线路、条目查询都走 emby-sidecar 管理端口；
    只有图片（排行榜封面、内联搜索海报）从公网 Emby 地址获取（由 nginx 转给 Emby 原后端并缓存，无需 API Key）。
    """

    def __init__(self, public_url):
        """
        :param public_url: 公网访问地址，如 https://tv.micu.hk（用于图片）
        """
        self.url = (public_url or "").rstrip("/")
        self.headers = {
            'accept': 'image/*,application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82'
        }

    # ───────── sidecar 管理端口 ─────────
    # 账号的创建 / 删除 / 改密 / 禁用、线路、条目查询都在 sidecar 完成，Emby 原后端只负责刮削与图片。

    @staticmethod
    def _sidecar_base():
        return (sidecar_url or "").rstrip("/")

    @staticmethod
    def _sidecar_headers():
        headers = {"accept": "application/json", "content-type": "application/json"}
        if sidecar_admin_token:
            headers["X-Admin-Token"] = sidecar_admin_token
        return headers

    def _sidecar(self, method, path, timeout=10, **kwargs):
        return r.request(method, f"{self._sidecar_base()}{path}", headers=self._sidecar_headers(), timeout=timeout, **kwargs)

    def _internal_parental_rating_url(self):
        return f"{sidecar_url.rstrip('/')}/internal/parental-rating"

    def _internal_use_line_url(self):
        return f"{sidecar_url.rstrip('/')}/internal/use-line"

    def _internal_user_last_activity_url(self):
        return f"{sidecar_url.rstrip('/')}/internal/user-last-activity"

    def _internal_session_count_url(self):
        return f"{sidecar_url.rstrip('/')}/internal/session-count"

    def _internal_play_count_ranks_url(self):
        return f"{sidecar_url.rstrip('/')}/internal/play-count-ranks"

    def _internal_item_other_name_url(self):
        return f"{sidecar_url.rstrip('/')}/internal/item-other-name"

    def _internal_auth_tokens_clear_url(self):
        return f"{sidecar_url.rstrip('/')}/internal/auth-tokens/clear"

    async def emby_create(self, tg: int, name, pwd2, us: int):
        """
        创建账户（sidecar 本地账号）
        :param tg: tg_id
        :param name: emby_name
        :param pwd2: pwd2 安全码
        :param us: us 积分
        :return: (pwd, ex) 成功；100 重名或 sidecar 不可用
        """
        ex = (datetime.now() + timedelta(days=us))
        pwd = await pwd_create(8)
        try:
            res = self._sidecar("POST", "/admin/users", json={"Name": name, "Password": pwd})
        except Exception as e:
            LOGGER.error(f"创建账户失败：sidecar 不可用 name={name} error={e}")
            return 100
        if res.status_code == 409:
            return 100
        if res.status_code != 200:
            LOGGER.error(f"创建账户失败：name={name} HTTP {res.status_code} body={res.text[:200]}")
            return 100
        id = res.json()["Id"]
        sql_update_emby(Emby.tg == tg, embyid=id, name=name, pwd=pwd, pwd2=pwd2, lv='b',
                        cr=datetime.now(), ex=ex, us=0)
        return pwd, ex.strftime("%Y-%m-%d %H:%M:%S")

    async def emby_del(self, id):
        """
        删除账户
        :param id: emby_id
        :return: bool
        """
        managed_user = sql_get_emby(id)
        try:
            res = self._sidecar("DELETE", f"/admin/users/{id}")
        except Exception as e:
            LOGGER.error(f"删除账户失败：sidecar 不可用 id={id} error={e}")
            return False
        # 404：sidecar 中已不存在，按删除成功处理以便清理本地记录
        if res.status_code not in (200, 204, 404):
            return False
        if not sql_delete_favorites_by_embyid(id):
            LOGGER.warning(f"删除账号 {id} 后清理收藏记录失败，不影响主流程")
        if managed_user is None:
            return True
        if sql_update_emby(Emby.embyid == id, embyid=None, name=None, pwd=None, pwd2=None, lv='d', cr=None,
                           ex=None):
            _open.tem = max(_open.tem - 1, 0)
            save_config()
            return True
        return False

    async def emby_reset(self, id, new=None):
        """
        重置密码（sidecar 会同时让该账号所有设备下线）
        :param id: emby_id
        :param new: new_pwd，None 表示重置为空密码
        :return: bool
        """
        body = {"ResetPassword": True} if new is None else {"NewPw": f"{new}"}
        try:
            res = self._sidecar("POST", f"/admin/users/{id}/password", json=body)
        except Exception as e:
            LOGGER.error(f"重置密码失败：sidecar 不可用 id={id} error={e}")
            return False
        if res.status_code != 200:
            return False
        return sql_update_emby(Emby.embyid == id, pwd=new) is True

    def clear_sidecar_auth_tokens(self, user_id):
        if not sidecar_url:
            LOGGER.warning(f"跳过 Sidecar token 清理：未配置 sidecar_url，user_id={user_id}")
            return False
        try:
            resp = self._sidecar("POST", "/internal/auth-tokens/clear", timeout=5, params={"userid": user_id})
            if resp.status_code not in (200, 204):
                LOGGER.error(f"清理 Sidecar token 失败：user_id={user_id}, HTTP {resp.status_code}, body={resp.text[:200]}")
                return False
            payload = resp.json() if resp.content else {}
            LOGGER.info(f"已通知 Sidecar 清理 token：user_id={user_id}, count={payload.get('ClearedTokenCount', 0)}")
            return True
        except Exception as e:
            LOGGER.error(f"清理 Sidecar token 异常：user_id={user_id}, error={e}")
            return False

    @cache.memoize(ttl=10)
    def get_current_playing_count(self) -> int:
        """
        最近播放数量
        :return: int NowPlayingItem
        """
        response = r.get(
            self._internal_session_count_url(),
            headers=self._sidecar_headers(),
            timeout=3
        )
        response.raise_for_status()
        payload = response.json()
        return int(payload.get("ActiveSessionCount", 0))

    async def emby_change_policy(self, id=id, admin=False, method=False):
        """
        :param id:
        :param admin: 已无效（sidecar 不提供管理员账号）
        :param method: True 禁用账号（并让所有设备下线），False 允许播放
        :return: 只有 sidecar 返回 200 且回传的 Policy.IsDisabled 与目标一致才算成功
        """
        want = bool(method)
        try:
            res = self._sidecar("POST", f"/admin/users/{id}/policy", json={"IsDisabled": want})
        except Exception as e:
            LOGGER.error(f"修改账号状态失败：id={id} error={e}")
            return False
        if res.status_code != 200:
            LOGGER.error(f"修改账号状态失败：id={id} HTTP {res.status_code} body={res.text[:200]}")
            return False
        try:
            got = res.json()["Policy"]["IsDisabled"]
        except Exception as e:
            LOGGER.error(f"修改账号状态失败：id={id} 响应无法解析 error={e} body={res.text[:200]}")
            return False
        if bool(got) != want:
            LOGGER.error(f"修改账号状态失败：id={id} 目标 IsDisabled={want}，sidecar 返回 {got}")
            return False
        return True

    async def ensure_enabled(self, id):
        """
        续费前确保 sidecar 中账号处于可用状态：已可用直接返回 True；被禁用则解封并确认。
        用于 lv=b 但 sidecar 仍是禁用（之前到期禁用后数据库没写成 c）等不一致情况。
        :return: 只有确认 sidecar 中账号可用才返回 True
        """
        ok, data = self.user(id)
        if ok:
            try:
                if not data["Policy"]["IsDisabled"]:
                    return True
            except Exception as e:
                LOGGER.error(f"查询账号状态失败：id={id} 响应无法解析 error={e}")
        LOGGER.info(f"续费解封：id={id} 当前{'被禁用' if ok else '状态未知'}，执行解封")
        return await self.emby_change_policy(id=id, method=False)

    async def authority_account(self, tg, username, password=None):
        """只校验账号密码，不产生登录会话。password 为 'None' 表示空密码。"""
        pw = "" if password in (None, 'None') else password
        try:
            res = self._sidecar("POST", "/admin/users/authenticate", json={"Username": username, "Pw": pw})
        except Exception as e:
            LOGGER.error(f"校验账号失败：sidecar 不可用 name={username} error={e}")
            return False, 0
        if res.status_code == 200:
            return True, res.json()["User"]["Id"]
        return False, 0

    async def users(self):
        """
        获取全部账号（sidecar），结构与 Emby UserDto 一致（含 Policy）。
        :return: (True, list) / (False, {'error': ...})
        """
        try:
            resp = self._sidecar("GET", "/admin/users", timeout=30)
            if resp.status_code != 200:
                return False, {'error': "🤕Sidecar 服务器连接失败!"}
            return True, resp.json()
        except Exception as e:
            return False, {'error': e}

    def user(self, embyid):
        """
        通过id查看该账户配置信息
        :param embyid:
        :return:
        """
        try:
            resp = self._sidecar("GET", f"/admin/users/{embyid}")
            if resp.status_code != 200:
                return False, {'error': "🤕Sidecar 服务器连接失败!"}
            return True, resp.json()
        except Exception as e:
            return False, {'error': e}

    async def add_favotire_items(self, user_id, item_id):
        """代用户收藏（sidecar 会同时推送收藏通知回本 bot 的 /webhook/favorites）。"""
        try:
            resp = self._sidecar("POST", f"/admin/users/{user_id}/favorites/{item_id}")
            return resp.status_code in (200, 204)
        except Exception as e:
            LOGGER.error(f'添加收藏失败 {e}')
            return False

    async def item_id_namme(self, user_id, item_id):
        try:
            reqs = self._sidecar("GET", f"/admin/users/{user_id}/items/{item_id}", timeout=3)
            if reqs.status_code != 200:
                return ''
            return reqs.json().get("Name")
        except Exception as e:
            LOGGER.error(f'获取title失败 {e}')
            return ''

    async def primary(self, item_id, width=200, height=300, quality=90):
        try:
            _url = f"{self.url}/emby/Items/{item_id}/Images/Primary?maxHeight={height}&maxWidth={width}&quality={quality}"
            resp = r.get(_url, headers=self.headers)
            if resp.status_code != 204 and resp.status_code != 200:
                return False, {'error': "🤕Emby 服务器连接失败!"}
            return True, resp.content
        except Exception as e:
            return False, {'error': e}

    async def backdrop(self, item_id, width=300, quality=90):
        try:
            _url = f"{self.url}/emby/Items/{item_id}/Images/Backdrop?maxWidth={width}&quality={quality}"
            resp = r.get(_url, headers=self.headers)
            if resp.status_code != 204 and resp.status_code != 200:
                return False, {'error': "🤕Emby 服务器连接失败!"}
            return True, resp.content
        except Exception as e:
            return False, {'error': e}

    async def items(self, user_id, item_id):
        """按 id 取条目详情（sidecar；user_id 仅为兼容旧调用，已不使用）。"""
        ok, data = self._sidecar_result("GET", f"/admin/items/{item_id}")
        if not ok:
            return False, {'error': data}
        return True, data

    async def get_sidecar_play_count_ranks(self, days=7, limit=10):
        try:
            response = r.get(
                self._internal_play_count_ranks_url(),
                headers=self._sidecar_headers(),
                params={"days": days, "limit": limit},
                timeout=10
            )
            if response.status_code not in (200, 204):
                return False, {'error': "🤕Sidecar 服务器连接失败!"}
            payload = response.json()
            movies = [
                ('', item.get("ItemId"), item.get("ItemType"), item.get("Name"), item.get("PlayCount"), item.get("TotalDuration", 0))
                for item in payload.get("Movies", [])
            ]
            tvs = [
                ('', item.get("ItemId"), item.get("ItemType"), item.get("Name"), item.get("PlayCount"), item.get("TotalDuration", 0))
                for item in payload.get("Series", [])
            ]
            return True, {"Movies": movies, "Series": tvs}
        except Exception as e:
            return False, {'error': e}

    async def get_sidecar_user_last_activity(self, user_id):
        try:
            response = r.get(
                self._internal_user_last_activity_url(),
                headers=self._sidecar_headers(),
                params={"userid": user_id},
                timeout=5
            )
            if response.status_code not in (200, 204):
                return False, {'error': "🤕Sidecar 服务器连接失败!"}
            return True, response.json()
        except Exception as e:
            return False, {'error': e}

    async def get_item_other_name(self, item_id):
        try:
            response = r.get(
                self._internal_item_other_name_url(),
                headers=self._sidecar_headers(),
                params={"item_id": item_id},
                timeout=5
            )
            if response.status_code == 404:
                return False, {'error': "未找到此 item_id"}
            if response.status_code not in (200, 204):
                return False, {'error': f"HTTP {response.status_code}"}
            return True, response.json()
        except Exception as e:
            LOGGER.error(f"获取别名失败: {e}")
            return False, {'error': e}

    async def set_item_other_name(self, item_id, other_name):
        try:
            response = r.get(
                self._internal_item_other_name_url(),
                headers=self._sidecar_headers(),
                params={"item_id": item_id, "other_name": other_name},
                timeout=5
            )
            if response.status_code == 404:
                return False, {'error': "未找到此 item_id"}
            if response.status_code not in (200, 204):
                return False, {'error': f"HTTP {response.status_code}"}
            return True, response.json()
        except Exception as e:
            LOGGER.error(f"设置别名失败: {e}")
            return False, {'error': e}

    @staticmethod
    def get_medias_count():
        """
        获得电影、电视剧、音乐媒体数量
        :return: MovieCount SeriesCount SongCount
        """
        try:
            res = r.get(url=f"{Embyservice._sidecar_base()}/admin/items/counts", headers=Embyservice._sidecar_headers(), timeout=5)
            if res.status_code == 200:
                result = res.json()
                # print(result)
                movie_count = result.get("MovieCount") or 0
                tv_count = result.get("SeriesCount") or 0
                episode_count = result.get("EpisodeCount") or 0
                music_count = result.get("SongCount") or 0
                txt = f'🎬 电影数量：{movie_count}\n' \
                      f'📽️ 剧集数量：{tv_count}\n' \
                      f'🎵 音乐数量：{music_count}\n' \
                      f'🎞️ 总集数：{episode_count}\n'
                return txt
            else:
                LOGGER.error(f"Items/Counts 未获取到返回数据")
                return None
        except Exception as e:
            LOGGER.error(f"连接Items/Counts出错：" + str(e))
            return e

    async def get_movies(self, title: str, start: int = 0, limit: int = 5):
        """
        根据标题搜索媒体库中的电影 / 剧集（sidecar），返回列表
        :param limit: x限制条目
        :param title: 标题
        :param start: 从何处开始
        :return: 返回信息列表
        """
        # 搜索走 sidecar（Meilisearch 增强搜索 + 完整详情）；封面图片仍由 Emby 原后端提供
        try:
            res = self._sidecar("GET", "/admin/items/search", timeout=5,
                                params={"q": title, "start": start, "limit": limit})
            if res.status_code == 200:
                res_items = res.json().get("Items")
                if res_items:
                    ret_movies = []
                    for res_item in res_items:
                        # print(res_item)
                        title = res_item.get("Name") if res_item.get("Name") == res_item.get(
                            "OriginalTitle") else f'{res_item.get("Name")} - {res_item.get("OriginalTitle")}'
                        od = ", ".join(res_item.get("ProductionLocations", ["普""遍"]))
                        ns = ", ".join(res_item.get("Genres", "未知"))
                        runtime = convert_runtime(res_item.get("RunTimeTicks")) if res_item.get(
                            "RunTimeTicks") else '数据缺失'
                        item_tmdbid = res_item.get("ProviderIds", {}).get("Tmdb", None)
                        # studios = ", ".join([item["Name"] for item in res_item.get("Studios", [])])
                        mediaserver_item = dict(item_type=res_item.get("Type"), item_id=res_item.get("Id"), title=title,
                                                year=res_item.get("ProductionYear", '缺失'),
                                                od=od, genres=ns,
                                                photo=f'{self.url}/emby/Items/{res_item.get("Id")}/Images/Primary?maxHeight=400&maxWidth=600&quality=90',
                                                runtime=runtime,
                                                overview=res_item.get("Overview", "暂无更多信息"),
                                                taglines='简介：' if not res_item.get("Taglines") else
                                                res_item.get("Taglines")[0],
                                                tmdbid=item_tmdbid,
                                                add=res_item.get("DateCreated", "None.").split('.')[0],
                                                # studios=studios
                                                )
                        ret_movies.append(mediaserver_item)
                    return ret_movies
        except Exception as e:
            LOGGER.error(f"连接Items出错：" + str(e))
            return []

    async def get_parental_rating(self, user_id):
        try:
            resp = r.get(
                self._internal_parental_rating_url(),
                headers=self._sidecar_headers(),
                params={"userid": user_id},
                timeout=5
            )
            if resp.status_code not in (200, 204):
                return False, f"HTTP {resp.status_code}"
            data = resp.json()
            return True, int(data.get("MaxParentalRatingValue", 10))
        except Exception as e:
            LOGGER.error(f"获取家长控制状态失败: {e}")
            return False, str(e)

    async def set_parental_rating(self, user_id, value: int):
        try:
            resp = r.get(
                self._internal_parental_rating_url(),
                headers=self._sidecar_headers(),
                params={"userid": user_id, "value": value},
                timeout=5
            )
            if resp.status_code == 423:
                return False, "家长控制已在网页控制面板锁定，请先在网页端用登录密码解锁"
            if resp.status_code not in (200, 204):
                return False, f"HTTP {resp.status_code}"
            data = resp.json()
            return True, int(data.get("MaxParentalRatingValue", value))
        except Exception as e:
            LOGGER.error(f"设置家长控制状态失败: {e}")
            return False, str(e)

    async def get_use_line(self, user_id):
        try:
            resp = r.get(
                self._internal_use_line_url(),
                headers=self._sidecar_headers(),
                params={"userid": user_id},
                timeout=5
            )
            if resp.status_code not in (200, 204):
                return False, f"HTTP {resp.status_code}"
            data = resp.json()
            return True, int(data.get("UseLine", 1))
        except Exception as e:
            LOGGER.error(f"获取线路状态失败: {e}")
            return False, str(e)

    async def set_use_line(self, user_id, value: int):
        """幂等设置 Sidecar 线路，并对超时后的实际成功进行回查确认。"""
        try:
            requested_value = int(value)
        except (TypeError, ValueError):
            return False, f"无效线路编号：{value}"

        # Sidecar 对“重复设置当前线路”可能返回 404，先读取可直接规避。
        current_ok, current_value = await self.get_use_line(user_id)
        if current_ok and current_value == requested_value:
            return True, current_value

        set_error = None
        try:
            resp = r.get(
                self._internal_use_line_url(),
                headers=self._sidecar_headers(),
                params={"userid": user_id, "value": requested_value},
                timeout=5
            )
            if resp.status_code in (200, 204):
                if resp.status_code == 200:
                    data = resp.json()
                    result = int(data.get("UseLine", requested_value))
                    if result == requested_value:
                        return True, result
                    set_error = f"后台返回线路 {result}，与目标线路不一致"
                else:
                    # 204 没有响应体，交由下面的实际状态回查确认。
                    set_error = "HTTP 204 未返回线路状态"
            else:
                set_error = f"HTTP {resp.status_code}"
        except Exception as e:
            set_error = str(e)

        # 请求可能已在 Sidecar 生效，但响应因超时、断网或 404 丢失。
        # 以后台最终状态为准，避免前台误报失败并显示旧线路。
        verified, actual_value = await self.get_use_line(user_id)
        if verified and actual_value == requested_value:
            LOGGER.warning(
                f"设置线路请求返回异常但后台已生效：user_id={user_id}, "
                f"line={requested_value}, response={set_error or 'unexpected result'}"
            )
            return True, actual_value

        LOGGER.error(
            f"设置线路状态失败：user_id={user_id}, line={requested_value}, "
            f"response={set_error or 'unexpected result'}, "
            f"actual={actual_value if verified else 'unavailable'}"
        )
        return False, set_error or actual_value

    # async def get_remote_image_by_id(self, item_id: str, image_type: str):
    #     """
    # 废物片段 西内！！！
    #     根据ItemId从Emby查询TMDB的图片地址
    #     :param item_id: 在Emby中的ID
    #     :param image_type: 图片的类弄地，poster或者backdrop等
    #     :return: 图片对应在TMDB中的URL
    #     """
    #     req_url = f"{self.url}/emby/Items/{item_id}/RemoteImages"
    #     try:
    #         res = r.get(url=req_url, headers=self.headers,timeout=3)
    #         if res:
    #             images = res.json().get("Images")
    #             if not images:
    #                 return f'{self.url}/emby/Items/{item_id}/Images/Primary?maxHeight=400&maxWidth=600&quality=90'
    #             for image in images:
    #                 # if image.get("ProviderName") in ["TheMovieDb", "MetaTube"] and image.get("Type") == image_type:
    #                 if image.get("Type") == image_type:
    #                     # print(image.get("Url"))
    #                     return image.get("Url")
    #         else:
    #             LOGGER.error(f"Items/RemoteImages 未获取到返回数据")
    #             return None
    #     except Exception as e:
    #         LOGGER.error(f"连接Items/Id/RemoteImages出错：" + str(e))
    #         return None
    #     return None


    # ───────── 线路管理（线路与 Pro 标定保存在 sidecar） ─────────

    def get_lines(self):
        """返回 (True, {"lines": [{id,name,pro,sort}], "defaultLineId": int}) 或 (False, 错误)"""
        try:
            resp = self._sidecar("GET", "/admin/lines", timeout=5)
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"
            return True, resp.json()
        except Exception as e:
            return False, str(e)

    def upsert_line(self, line_id: int, name: str, pro: bool, sort=None):
        body = {"Name": name, "Pro": bool(pro)}
        if sort is not None:
            body["Sort"] = int(sort)
        return self._sidecar_result("PUT", f"/admin/lines/{int(line_id)}", json=body)

    def delete_line(self, line_id: int):
        return self._sidecar_result("DELETE", f"/admin/lines/{int(line_id)}")

    def set_default_line(self, line_id: int):
        return self._sidecar_result("POST", "/admin/lines/default", json={"Id": int(line_id)})

    def _sidecar_result(self, method, path, **kwargs):
        try:
            resp = self._sidecar(method, path, **kwargs)
            data = resp.json() if resp.content else {}
            if resp.status_code != 200:
                return False, data.get("error") or f"HTTP {resp.status_code}"
            return True, data
        except Exception as e:
            return False, str(e)

    # ───────── 额外账号（不绑定 TG，但记录在 emby 表） ─────────

    async def create_extra_account(self, name):
        """在 sidecar 创建账号并写入 emby 表（tg 取 1~99999 的占位编号，等级 a 不过期）。返回 (True, (tg, pwd, pwd2)) / (False, 原因)"""
        from bot.sql_helper.sql_extra import sql_add_extra_account
        pwd = await pwd_create(8)
        pwd2 = await pwd_create(4)
        ok, data = self._sidecar_result("POST", "/admin/users", json={"Name": name, "Password": pwd})
        if not ok:
            return False, "已有同名账号" if "exists" in str(data) else data
        tg = sql_add_extra_account(embyid=data["Id"], name=name, pwd=pwd, pwd2=pwd2)
        if tg is None:
            # 数据库写入失败时回滚 sidecar 账号，避免产生未绑定账号
            self._sidecar_result("DELETE", f"/admin/users/{data['Id']}")
            return False, "写入 embyboss 数据库失败"
        return True, (tg, pwd, pwd2)


# 实例
emby = Embyservice(emby_public_url)
