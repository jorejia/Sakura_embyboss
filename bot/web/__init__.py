#! /usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio
import errno

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .api import emby_api_route
from bot import api as config_api, LOGGER


class Web:
    def __init__(self):
        self.app: FastAPI = FastAPI()
        self.web_api = None
        self.start_api = None

    def init_api(self):
        self.app.include_router(emby_api_route)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config_api.allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def start(self):
        if not config_api.status:
            LOGGER.info("【API服务】未开启，跳过 WebHook 服务启动")
            return

        LOGGER.info("【API服务】检测到已开启，正在启动 WebHook 服务")
        import uvicorn

        self.init_api()
        self.web_api = uvicorn.Server(
            config=uvicorn.Config(self.app, host=config_api.http_url, port=config_api.http_port)
        )
        server_config = self.web_api.config
        if not server_config.loaded:
            server_config.load()
        self.web_api.lifespan = server_config.lifespan_class(server_config)
        try:
            await self.web_api.startup()
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                LOGGER.error(f"【API服务】端口 {config_api.http_port} 被占用，请修改配置")
            raise SystemExit from None
        if self.web_api.should_exit:
            raise SystemExit from None
        LOGGER.info("【API服务】WebHook 服务启动成功")

    def stop(self):
        if self.start_api:
            LOGGER.info("正在停止 API 服务...")
            try:
                self.start_api.cancel()
                asyncio.run(self.start_api)
            except asyncio.CancelledError:
                pass
            finally:
                LOGGER.info("API 服务已停止")


check = Web()
loop = asyncio.get_event_loop()
loop.create_task(check.start())
