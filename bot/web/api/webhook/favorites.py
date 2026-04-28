import json

from fastapi import APIRouter, Request

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
    action = "收藏" if is_favorite else "取消收藏"
    try:
        await bot.send_message(
            chat_id=tg_id,
            text=f"📢 您的 Emby 账号 {embyname} {action}了《{item_name}》",
        )
    except Exception as e:
        LOGGER.error(f"发送收藏通知失败: {str(e)}")


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
        is_favorite = item_data.get("UserData", {}).get("IsFavorite", False)

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
