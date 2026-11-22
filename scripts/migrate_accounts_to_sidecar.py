#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性迁移：把账号状态从 Emby 原后端 / embyboss 数据库迁到 emby-sidecar。

做四件事（都可重复执行）：
  1. 禁用状态：读 Emby 原后端的用户 Policy.IsDisabled，写入 sidecar（媒体库屏蔽已废弃，不迁移）。
  4. 首页布局：读 Emby 用户 Configuration 的 OrderedViews / LatestItemsExcludes / MyMediaExcludes，
     把媒体库 Guid 换成 sidecar 使用的数字 Id 后写入（只写 sidecar 中尚未设置过的键，不覆盖迁移后用户的新设置）。
  2. 密码：embyboss 的 emby 表保存了明文密码（pwd，None 表示已重置为空密码），写入 sidecar。
     例外：额外账号（tg 1~99999）pwd 为 None 表示密码未知，跳过，不会被置为空密码。
     默认只写“尚未迁移”的账号（sidecar password_hash 为 NULL），不会覆盖迁移后用户改过的密码；--force-password 强制覆盖。
  3. 报告：sidecar 里存在但 embyboss 未绑定的账号、embyboss 里有 embyid 但 sidecar 不存在的账号。

用法（在 embyboss 根目录，读取 config.json；Emby 原后端地址与 API Key 已不在配置文件里，通过参数传入）：
  python scripts/migrate_accounts_to_sidecar.py --emby-url http://127.0.0.1:8096 --emby-api <管理员 API Key> --dry-run
  python scripts/migrate_accounts_to_sidecar.py --emby-url http://127.0.0.1:8096 --emby-api <管理员 API Key>
  python scripts/migrate_accounts_to_sidecar.py --skip-emby        # Emby 用户已清理后只迁密码
"""
import argparse
import json
import sys

import pymysql
import requests


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Sidecar:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.headers = {"accept": "application/json", "content-type": "application/json"}
        if token:
            self.headers["X-Admin-Token"] = token

    def call(self, method, path, **kwargs):
        resp = requests.request(method, self.base + path, headers=self.headers, timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json() if resp.content else None


def emby_user(emby, user_id):
    url = emby["url"] + f"/emby/Users/{user_id}"
    resp = requests.get(url, headers={"X-Emby-Token": emby["api"], "accept": "application/json"}, timeout=15)
    if resp.status_code == 404 or resp.status_code == 400:
        return None
    resp.raise_for_status()
    return resp.json()


def emby_library_guids(emby):
    """Emby 的 OrderedViews 等存的是媒体库 Guid，sidecar 用数字 Id：建立 Guid -> Id 映射。"""
    resp = requests.get(emby["url"] + "/emby/Library/MediaFolders", headers={"X-Emby-Token": emby["api"]}, timeout=30)
    resp.raise_for_status()
    out = {}
    for item in resp.json().get("Items") or []:
        guid = (item.get("Guid") or "").replace("-", "").lower()
        if guid:
            out[guid] = str(item["Id"])
        out[str(item["Id"])] = str(item["Id"])
    return out


HOME_KEYS = ("OrderedViews", "LatestItemsExcludes", "MyMediaExcludes")


def home_config(emby_cfg, guid_map):
    """把 Emby Configuration 里的首页布局转换成 sidecar 的数字 Id；没有任何自定义时返回空。"""
    out = {}
    for key in HOME_KEYS:
        values = emby_cfg.get(key) or []
        mapped = [guid_map[v.replace("-", "").lower()] for v in values if v and v.replace("-", "").lower() in guid_map]
        if mapped:
            out[key] = mapped
    return out


def embyboss_accounts(cfg):
    conn = pymysql.connect(host=cfg["db_host"], user=cfg["db_user"], password=cfg["db_pwd"],
                           database=cfg["db_name"], port=int(cfg.get("db_port") or 3306), charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT tg, embyid, name, pwd, lv FROM emby WHERE embyid IS NOT NULL AND embyid <> ''")
            rows = cur.fetchall()
    finally:
        conn.close()
    out = {}
    for tg, embyid, name, pwd, lv in rows:
        out[embyid.replace("-", "").lower()] = {"tg": tg, "name": name, "pwd": pwd, "lv": lv}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要做的修改")
    parser.add_argument("--skip-emby", action="store_true", help="不读取 Emby 原后端的用户策略")
    parser.add_argument("--force-password", action="store_true", help="覆盖 sidecar 中已存在的密码")
    parser.add_argument("--emby-url", default="", help="Emby 原后端地址（如 http://127.0.0.1:8096）")
    parser.add_argument("--emby-api", default="", help="Emby 管理员 API Key")
    args = parser.parse_args()

    cfg = load_config(args.config)
    emby = {"url": (args.emby_url or cfg.get("emby_url") or "").rstrip("/"), "api": args.emby_api or cfg.get("emby_api") or ""}
    if not args.skip_emby and (not emby["url"] or not emby["api"]):
        parser.error("需要 --emby-url 与 --emby-api（或使用 --skip-emby 跳过禁用状态与首页布局迁移）")
    guid_map = {} if args.skip_emby else emby_library_guids(emby)
    sidecar = Sidecar(cfg["sidecar_url"], cfg.get("sidecar_admin_token") or "")
    users = sidecar.call("GET", "/admin/users")
    bound = embyboss_accounts(cfg)
    print(f"sidecar 账号 {len(users)} 个，embyboss 已绑定 {len(bound)} 个")

    stats = {"policy": 0, "policy_skip": 0, "home": 0, "home_kept": 0, "pwd_imported": 0, "pwd_kept": 0, "pwd_unknown": 0, "pwd_missing": 0, "unbound": 0}
    sidecar_ids = set()
    for user in users:
        uid = user["Id"]
        sidecar_ids.add(uid)
        name = user["Name"]

        if not args.skip_emby:
            try:
                eu = emby_user(emby, uid)
            except Exception as e:  # noqa: BLE001
                print(f"[WARN] 读取 Emby 用户 {name}({uid}) 失败：{e}")
                eu = None
            if eu and eu.get("Policy"):
                # embyboss 是账号状态的权威：lv=c（已封禁/到期）即使 Emby 里没禁用也按禁用处理
                boss = bound.get(uid.replace("-", "").lower())
                disabled = bool(eu["Policy"].get("IsDisabled")) or (boss is not None and boss["lv"] == "c")
                current = user.get("Policy") or {}
                if bool(current.get("IsDisabled")) != disabled:
                    print(f"[POLICY] {name}: IsDisabled={disabled}")
                    if not args.dry_run:
                        sidecar.call("POST", f"/admin/users/{uid}/policy", json={"IsDisabled": disabled})
                    stats["policy"] += 1
                else:
                    stats["policy_skip"] += 1
            if eu:
                home = home_config(eu.get("Configuration") or {}, guid_map)
                if home:
                    if args.dry_run:
                        stats["home"] += 1
                    else:
                        written = sidecar.call("POST", f"/admin/users/{uid}/configuration",
                                               json={"Configuration": home, "OnlyMissing": True}).get("Written") or []
                        stats["home" if written else "home_kept"] += 1

        acc = bound.get(uid)
        if acc is None:
            stats["unbound"] += 1
            print(f"[UNBOUND] sidecar 账号 {name}({uid}) 未在 embyboss 绑定")
            continue
        # 额外账号（tg 1~99999）若没有记录密码，说明密码只在 Emby 里：不导入空密码，
        # 留给 LEGACY_AUTH_FALLBACK 首次登录回源校验，或在管理菜单「额外账号」里重置
        if acc["pwd"] is None and 1 <= int(acc["tg"]) <= 99999:
            if not user.get("PasswordMigrated"):
                print(f"[PWD?] 额外账号 {name} 未记录密码，跳过（首次登录回源 Emby 校验或手动重置）")
                stats["pwd_unknown"] += 1
            else:
                stats["pwd_kept"] += 1
            continue
        password = acc["pwd"] if acc["pwd"] is not None else ""
        if args.force_password:
            print(f"[PWD] 覆盖 {name}")
            if not args.dry_run:
                sidecar.call("POST", f"/admin/users/{uid}/password", json={"NewPw": password})
            stats["pwd_imported"] += 1
        elif user.get("PasswordMigrated"):
            stats["pwd_kept"] += 1
        else:
            print(f"[PWD] 导入 {name}{'（空密码）' if password == '' else ''}")
            if not args.dry_run:
                result = sidecar.call("POST", f"/admin/users/{uid}/password/import", json={"Password": password})
                if not result.get("Imported"):
                    stats["pwd_kept"] += 1
                    continue
            stats["pwd_imported"] += 1

    for uid, acc in bound.items():
        if uid not in sidecar_ids:
            stats["pwd_missing"] += 1
            print(f"[MISSING] embyboss 绑定的 {acc['name']}({uid}, tg={acc['tg']}) 在 sidecar 中不存在")

    print("完成：" + json.dumps(stats, ensure_ascii=False))
    if args.dry_run:
        print("（dry-run，未写入任何修改）")


if __name__ == "__main__":
    sys.exit(main())
