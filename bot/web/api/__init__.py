#! /usr/bin/python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Request

from .webhook.favorites import router as favorites_router
from .webhook.media import router as media_router
from bot import LOGGER, bot_token

emby_api_route = APIRouter(prefix="/emby", tags=["对接Emby的接口"])


async def verify_token(request: Request):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    if token != bot_token:
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
