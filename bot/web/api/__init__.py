#! /usr/bin/python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Request

from .webhook.favorites import router as favorites_router
from .webhook.media import router as media_router
import hmac

from bot import LOGGER, bot_token, sidecar_webhook_token

# 收藏变更与追剧更新现在由 emby-sidecar 推送（payload 与原 Emby Webhooks 相同）
emby_api_route = APIRouter(prefix="/emby", tags=["对接Emby的接口"])


async def verify_token(request: Request):
    # sidecar 推送时携带 X-Sidecar-Token（对应 sidecar 的 NOTIFY_WEBHOOK_TOKEN）
    sidecar_token = request.headers.get("X-Sidecar-Token")
    if sidecar_webhook_token and sidecar_token:
        if hmac.compare_digest(sidecar_token, sidecar_webhook_token):
            return True
        LOGGER.warning("Invalid X-Sidecar-Token attempt")
        raise HTTPException(status_code=403, detail="Invalid token")
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    if not hmac.compare_digest(token, bot_token):
        LOGGER.warning(f"Invalid token attempt: {token[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid token")
    return True


emby_api_route.include_router(
    favorites_router,
    dependencies=[Depends(verify_token)],
)
emby_api_route.include_router(
    media_router,
    dependencies=[Depends(verify_token)],
)
