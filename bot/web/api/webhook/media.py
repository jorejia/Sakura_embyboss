import json

from fastapi import APIRouter, Request

from bot import LOGGER, bot
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import Emby
from bot.sql_helper.sql_favorites import EmbyFavorites

router = APIRouter()


async def parse_webhook_payload(request: Request):
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        return await request.json()

    form_data = await request.form()
    form = dict(form_data)
    if "data" in form:
        return json.loads(form["data"])
    return None


async def send_update_notification_to_user(tg_id: int, message: str):
    try:
        await bot.send_message(chat_id=tg_id, text=message)
        return True
    except Exception as e:
        LOGGER.error(f"发送通知失败: {str(e)}")
        return False


def build_episode_message(item_data: dict) -> str:
    series_name = item_data.get("SeriesName") or item_data.get("Name") or "未知剧集"
    season_name = item_data.get("SeasonName", "")
    season_number = item_data.get("ParentIndexNumber")
    episode_number = item_data.get("IndexNumber")

    season_text = season_name
    if not season_text and season_number:
        season_text = f"第{season_number}季"

    episode_text = f"第 {episode_number} 集" if episode_number else "新一集"
    message = f"📺 您关注的剧集更新啦\n剧集：《{series_name}》\n更新：{episode_text}"
    if season_text:
        message = f"📺 您关注的剧集更新啦\n剧集：《{series_name}》 {season_text}\n更新：{episode_text}"
    return message


async def check_and_notify_series_update(item_data: dict):
    series_id = item_data.get("SeriesId")
    if not series_id:
        return 0

    with Session() as session:
        favorites = session.query(EmbyFavorites, Emby).join(
            Emby, EmbyFavorites.embyid == Emby.embyid
        ).filter(
            EmbyFavorites.item_id == series_id,
            Emby.tg.isnot(None),
            Emby.notify_enabled == 1,
        ).all()

    if not favorites:
        return 0

    notified_users = set()
    message = build_episode_message(item_data)
    for _, user in favorites:
        if not user.tg or user.tg in notified_users:
            continue
        await send_update_notification_to_user(user.tg, message)
        notified_users.add(user.tg)
    return len(notified_users)


@router.post("/webhook/medias")
async def handle_media_webhook(request: Request):
    """处理 Emby 媒体库更新事件，仅向收藏剧集的用户推送更新通知。"""
    try:
        webhook_data = await parse_webhook_payload(request)
        if not webhook_data:
            return {"status": "error", "message": "No data received"}

        event = webhook_data.get("Event", "")
        item_data = webhook_data.get("Item", {})
        if event not in ["item.added", "library.new"]:
            return {"status": "ignored", "message": "Not a new media event", "event": event}

        item_type = item_data.get("Type", "")
        if item_type == "Episode":
            count = await check_and_notify_series_update(item_data)
            return {
                "status": "success",
                "message": "Episode update notification processed",
                "data": {
                    "type": item_type,
                    "name": item_data.get("Name"),
                    "series": item_data.get("SeriesName"),
                    "event": event,
                    "notified": count,
                },
            }

        return {"status": "ignored", "message": "Unsupported media type", "event": event}
    except Exception as e:
        LOGGER.error(f"处理媒体 WebHook 失败: {str(e)}")
        return {"status": "error", "message": str(e)}
