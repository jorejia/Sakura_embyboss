import asyncio
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock


spec = importlib.util.spec_from_file_location(
    "telegram_reconnect", Path(__file__).parents[1] / "bot/func_helper/telegram_reconnect.py"
)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class TelegramReconnectTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.logger = Mock()
        self.started = asyncio.Event()
        self.started.set()
        self.session = SimpleNamespace(
            connection=object(), is_started=self.started, recv_task=None, ping_task=None,
            send=AsyncMock(return_value="response"), stop=AsyncMock(),
        )
        self.original_send = self.session.send
        self.original_stop = self.session.stop

        async def restart():
            await self.session.stop()
            self.session.connection = object()
            self.started.set()

        self.original_restart = AsyncMock(side_effect=restart)
        self.session.restart = self.original_restart
        self.original_watchdog = AsyncMock()
        self.client = SimpleNamespace(
            session=self.session, connect=AsyncMock(return_value=True), stop=AsyncMock(),
            updates_watchdog=self.original_watchdog,
        )
        self.controller = recovery.TelegramReconnect(
            self.client, self.logger, attempt_timeout=0.02, retry_delays=(0,)
        ).install()
        await self.client.connect()

    async def asyncTearDown(self):
        await self.client.stop()

    def reattach(self, send=None, stop=None):
        self.session.send = send if send is not None else self.original_send
        self.session.stop = stop if stop is not None else self.original_stop
        self.session.restart = self.original_restart
        self.controller.session = None
        self.controller.attach_session(self.session)

    async def test_install_and_normal_rpc_add_no_traffic_or_background_polling(self):
        self.assertEqual(await self.session.send("query"), "response")
        self.original_send.assert_awaited_once_with("query")
        self.assertIsNone(self.controller.reconnect_task)
        self.original_restart.assert_not_awaited()
        self.original_watchdog.assert_not_awaited()

    async def test_rpc_error_triggers_reconnect_without_replaying_business_request(self):
        send = AsyncMock(side_effect=OSError("TCPTransport closed=True"))
        # Re-attach a fresh session so the hook captures this method.
        self.reattach(send=send)
        with self.assertRaises(OSError):
            await self.session.send("send message")
        await self.controller.reconnect_task
        send.assert_awaited_once_with("send message")
        self.original_restart.assert_awaited_once()

    async def test_many_simultaneous_errors_share_one_reconnect(self):
        release = asyncio.Event()

        async def slow_restart():
            await release.wait()

        self.reattach(send=AsyncMock(side_effect=OSError("closed")))
        self.controller._original_restart = AsyncMock(side_effect=slow_restart)
        results = await asyncio.gather(
            *(self.session.send("query") for _ in range(30)), return_exceptions=True
        )
        self.assertTrue(all(isinstance(result, OSError) for result in results))
        release.set()
        await self.controller.reconnect_task
        self.controller._original_restart.assert_awaited_once()

    async def test_old_connection_error_does_not_restart_a_recovered_connection(self):
        old_connection = self.session.connection
        await self.session.restart()
        self.assertIsNone(self.controller.request_reconnect("late error", old_connection))
        self.original_restart.assert_awaited_once()

    async def test_native_receiver_reconnect_uses_same_recovery(self):
        await self.session.restart()
        self.original_restart.assert_awaited_once()

    async def test_network_outage_retries_then_recovers_in_process(self):
        self.controller._original_restart = AsyncMock(side_effect=[OSError("offline"), OSError("offline"), None])
        await self.controller.request_reconnect("network down")
        self.assertEqual(self.controller._original_restart.await_count, 3)
        self.assertFalse(self.controller.stopping)
        self.logger.info.assert_called_once()

    async def test_stuck_reconnect_is_cancelled_and_retried(self):
        attempts = 0
        cancelled = asyncio.Event()

        async def restart():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

        self.controller._original_restart = restart
        await asyncio.wait_for(self.controller.request_reconnect("stuck"), 1)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(attempts, 2)

    async def test_non_network_api_error_does_not_reconnect(self):
        send = AsyncMock(side_effect=ValueError("invalid API argument"))
        self.reattach(send=send)
        with self.assertRaises(ValueError):
            await self.session.send("query")
        self.assertIsNone(self.controller.reconnect_task)

    async def test_watchdog_survives_network_error_and_resumes_original_loop(self):
        self.original_watchdog.side_effect = [OSError("GetState failed"), None]
        await self.client.updates_watchdog()
        self.assertEqual(self.original_watchdog.await_count, 2)
        self.original_restart.assert_awaited_once()

    async def test_shutdown_cancels_reconnect_and_prevents_new_reconnections(self):
        entered = asyncio.Event()

        async def blocked():
            entered.set()
            await asyncio.Event().wait()

        self.controller._original_restart = blocked
        task = self.controller.request_reconnect("offline")
        await entered.wait()
        await self.client.stop()
        self.assertTrue(task.cancelled())
        self.assertIsNone(self.controller.request_reconnect("during shutdown"))

    async def test_dead_receiver_does_not_abort_session_stop(self):
        async def failed_receiver():
            raise RuntimeError("receiver transport failed")

        receiver = asyncio.create_task(failed_receiver())
        await asyncio.sleep(0)
        self.session.recv_task = receiver

        async def stop():
            if self.session.recv_task:
                await self.session.recv_task

        self.reattach(stop=stop)
        await self.session.restart()
        self.assertIsNone(self.session.recv_task)
        self.original_restart.assert_awaited_once()

    async def test_original_recursive_retries_trigger_only_one_recovery(self):
        calls = []

        self.reattach(send=AsyncMock(side_effect=OSError("closed")))

        async def invoke(query, retries=2):
            calls.append(retries)
            try:
                return await self.session.send(query)
            except OSError:
                if retries:
                    return await invoke(query, retries - 1)
                raise

        with self.assertRaises(OSError):
            await invoke("query")
        await self.controller.reconnect_task
        self.assertEqual(calls, [2, 1, 0])
        self.original_restart.assert_awaited_once()

    async def test_receiver_that_fails_during_cleanup_is_also_released(self):
        calls = 0

        async def failed_receiver():
            raise RuntimeError("receiver failed during stop")

        async def stop():
            nonlocal calls
            calls += 1
            if calls == 1:
                self.session.recv_task = asyncio.create_task(failed_receiver())
                await self.session.recv_task

        self.reattach(stop=stop)
        await self.session.restart()
        self.assertIsNone(self.session.recv_task)
        self.assertEqual(calls, 2)

    async def test_existing_heartbeat_send_error_triggers_recovery(self):
        self.reattach(send=AsyncMock(side_effect=OSError("heartbeat transport closed")))
        # Pyrogram's ping_worker ignores OSError; the send hook has already
        # scheduled recovery before that catch can swallow the error.
        try:
            await self.session.send("existing PingDelayDisconnect", False)
        except OSError:
            pass
        await self.controller.reconnect_task
        self.original_restart.assert_awaited_once()

    async def test_ambiguous_send_timeout_does_not_add_a_replay(self):
        send = AsyncMock(side_effect=TimeoutError("Request timed out"))
        self.reattach(send=send)
        with self.assertRaises(TimeoutError):
            await self.session.send("write operation")
        await self.controller.reconnect_task
        send.assert_awaited_once_with("write operation")

    async def test_cancelling_a_waiter_does_not_cancel_shared_reconnect(self):
        entered = asyncio.Event()
        release = asyncio.Event()

        async def restart():
            entered.set()
            await release.wait()

        self.controller._original_restart = restart
        waiter = asyncio.create_task(self.session.restart())
        await entered.wait()
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        self.assertFalse(self.controller.reconnect_task.done())
        release.set()
        await self.controller.reconnect_task


if __name__ == "__main__":
    unittest.main()
