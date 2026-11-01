"""Recover the main Pyrogram session using existing network error signals.

No polling, extra health RPCs, process restart, or automatic business-RPC replay.
The hooks target the Session lifecycle in Pyrogram 2.0.106.
"""
import asyncio


NETWORK_ERRORS = (OSError, asyncio.TimeoutError)


class TelegramReconnect:
    def __init__(self, client, logger, attempt_timeout=30, retry_delays=(2, 5, 10, 30)):
        self.client = client
        self.logger = logger
        self.attempt_timeout = attempt_timeout
        self.retry_delays = retry_delays
        self.stopping = False
        self.session = None
        self.reconnect_task = None

    def install(self):
        original_connect = self.client.connect
        original_stop = self.client.stop
        original_watchdog = self.client.updates_watchdog

        async def connect(*args, **kwargs):
            result = await original_connect(*args, **kwargs)
            self.stopping = False
            self.attach_session(self.client.session)
            return result

        async def stop(*args, **kwargs):
            self.stopping = True
            task = self.reconnect_task
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            return await original_stop(*args, **kwargs)

        async def updates_watchdog():
            while not self.stopping:
                try:
                    return await original_watchdog()
                except NETWORK_ERRORS as error:
                    # A failed GetState must not permanently kill this task.
                    if self.stopping:
                        return
                    task = self.request_reconnect(f"updates_watchdog: {error}")
                    if task is not None:
                        await asyncio.shield(task)

        self.client.connect = connect
        self.client.stop = stop
        self.client.updates_watchdog = updates_watchdog
        return self

    def attach_session(self, session):
        if session is self.session:
            return
        self.session = session
        original_send = session.send
        original_restart = session.restart
        original_stop = session.stop

        async def send(*args, **kwargs):
            # Both existing RPCs and Pyrogram's existing heartbeat use send().
            # React to their errors without adding probes or changing retries.
            connection = session.connection
            try:
                return await original_send(*args, **kwargs)
            except NETWORK_ERRORS as error:
                if session is self.session:
                    self.request_reconnect(f"send: {type(error).__name__}: {error}", connection)
                # Do not replay an ambiguous write/send after a timeout.
                raise

        async def restart():
            if session is self.session:
                task = self.request_reconnect("Pyrogram 接收任务检测到断线")
                if task is not None:
                    await asyncio.shield(task)

        async def stop():
            # Session.stop awaits these tasks. An already failed receiver/ping
            # must not abort cleanup before the connection can be reopened.
            self._discard_failed_tasks(session)
            try:
                await original_stop()
            except Exception:
                if not self._discard_failed_tasks(session):
                    raise
                await original_stop()

        session.send = send
        session.restart = restart
        session.stop = stop
        self._original_restart = original_restart

    def _discard_failed_tasks(self, session):
        discarded = False
        for name in ("recv_task", "ping_task"):
            task = getattr(session, name, None)
            if task is None or not task.done():
                continue
            error = None if task.cancelled() else task.exception()
            if task.cancelled() or error is not None:
                self.logger.warning(f"【Telegram重连】清理已失败的 {name}: {error!r}")
                setattr(session, name, None)
                discarded = True
        return discarded

    def request_reconnect(self, reason, failed_connection=None):
        if self.stopping or self.session is None:
            return None
        if self.reconnect_task is not None and not self.reconnect_task.done():
            return self.reconnect_task
        if (failed_connection is not None
                and self.session.connection is not failed_connection
                and self.session.is_started.is_set()):
            # Another request/the receiver has already restored this session.
            return None
        self.logger.warning(f"【Telegram重连】触发进程内恢复：{reason}")
        self.reconnect_task = asyncio.create_task(self._reconnect())
        self.reconnect_task.add_done_callback(self._reconnect_done)
        return self.reconnect_task

    async def _reconnect(self):
        attempt = 0
        while not self.stopping:
            attempt += 1
            try:
                await asyncio.wait_for(self._original_restart(), self.attempt_timeout)
            except NETWORK_ERRORS as error:
                delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                self.logger.warning(
                    f"【Telegram重连】第{attempt}次失败：{type(error).__name__}: {error}；"
                    f"{delay}秒后重试"
                )
                await asyncio.sleep(delay)
            else:
                self.logger.info(f"【Telegram重连】会话已恢复，共尝试{attempt}次")
                return

    def _reconnect_done(self, task):
        if not task.cancelled():
            error = task.exception()
            if error is not None:
                self.logger.error(f"【Telegram重连】非网络异常，停止本轮恢复：{error!r}")


def install_telegram_reconnect(client, logger):
    return TelegramReconnect(client, logger).install()
