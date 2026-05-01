import json

from fastapi import APIRouter, Request, Response

from bot import LOGGER, bot
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import Emby
from bot.sql_helper.sql_favorites import sql_add_favorites, EmbyFavorites

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


async def send_favorite_notification(tg_id: int, embyname: str, item_name: str, is_favorite: bool):
    try:
        text = (
            f"📢您收藏了《{item_name}》，将会获得追剧通知哦"
            if is_favorite
            else f"📢您已取消收藏《{item_name}》，不再获得其追剧通知"
        )
        await bot.send_message(
            chat_id=tg_id,
            text=text,
        )
    except Exception as e:
        LOGGER.error(f"发送收藏通知失败: {str(e)}")


async def send_text_notification(tg_id: int, text: str):
    try:
        await bot.send_message(chat_id=tg_id, text=text)
    except Exception as e:
        LOGGER.error(f"发送提示通知失败: {str(e)}")


def build_non_series_favorite_message(item_type: str) -> str:
    if item_type == "Season":
        return "您刚刚收藏了一个季条目，不会获得追剧提醒，如有需要请收藏剧集条目哦"
    if item_type == "Episode":
        return "您刚刚收藏了一个单集条目，不会获得追剧提醒，如有需要请收藏剧集条目哦"
    return "您刚刚收藏了一个非追剧条目，不会获得追剧提醒，如有需要请收藏剧集条目哦"


@router.post("/webhook/favorites")
async def handle_favorite_webhook(request: Request):
    """接收 Emby 收藏变更事件，并为追剧推送维护收藏关系。"""
    try:
        webhook_data = await parse_webhook_payload(request)
        if not webhook_data:
            return {"status": "error", "message": "No data received"}

        user_data = webhook_data.get("User", {})
        item_data = webhook_data.get("Item", {})
        embyid = user_data.get("Id", "")
        embyname = user_data.get("Name", "")
        item_id = item_data.get("Id", "")
        item_name = item_data.get("Name", "")
        item_type = item_data.get("Type", "")
        is_favorite = item_data.get("UserData", {}).get("IsFavorite", False)

        if item_type != "Series":
            if item_type == "Movie":
                return Response(status_code=204)
            if is_favorite:
                message = build_non_series_favorite_message(item_type)
            else:
                message = "您取消收藏了一个非追剧条目"

            with Session() as session:
                user = session.query(Emby).filter(Emby.embyid == embyid).first()
                if user and user.tg and user.notify_enabled == 1:
                    await send_text_notification(user.tg, message)

            return {
                "status": "ignored",
                "message": message,
                "data": {
                    "user": {"name": embyname, "id": embyid},
                    "item": {"name": item_name, "id": item_id, "type": item_type},
                    "is_favorite": is_favorite,
                    "event": webhook_data.get("Event", ""),
                    "date": webhook_data.get("Date", ""),
                },
            }

        with Session() as session:
            existing = session.query(EmbyFavorites).filter(
                EmbyFavorites.embyid == embyid,
                EmbyFavorites.item_id == item_id,
            ).first()

        state_changed = (existing is None and is_favorite) or (existing is not None and not is_favorite)
        if not state_changed:
            LOGGER.info(
                f"收藏事件忽略: event={webhook_data.get('Event', '')} embyid={embyid} "
                f"item_id={item_id} is_favorite={is_favorite} existing={bool(existing)}"
            )
            return {
                "status": "ignored",
                "message": "Favorite state unchanged",
                "data": {
                    "event": webhook_data.get("Event", ""),
                    "embyid": embyid,
                    "item_id": item_id,
                    "is_favorite": is_favorite,
                    "existing": bool(existing),
                },
            }

        save_result = sql_add_favorites(
            embyid=embyid,
            embyname=embyname,
            item_id=item_id,
            item_name=item_name,
            is_favorite=is_favorite,
        )
        if not save_result:
            return {"status": "error", "message": "Save favorite failed"}

        with Session() as session:
            user = session.query(Emby).filter(Emby.embyid == embyid).first()
            if user and user.tg and user.notify_enabled == 1:
                await send_favorite_notification(
                    tg_id=user.tg,
                    embyname=embyname,
                    item_name=item_name,
                    is_favorite=is_favorite,
                )

        return {
            "status": "success",
            "message": "Favorite event processed",
            "data": {
                "user": {"name": embyname, "id": embyid},
                "item": {"name": item_name, "id": item_id},
                "is_favorite": is_favorite,
                "event": webhook_data.get("Event", ""),
                "date": webhook_data.get("Date", ""),
            },
        }
    except Exception as e:
        LOGGER.error(f"处理收藏 WebHook 失败: {str(e)}")
        return {"status": "error", "message": str(e)}
