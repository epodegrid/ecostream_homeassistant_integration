from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import time
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError, WSMsgType
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from custom_components.ecostream.const import (
    WS_STALE_TIMEOUT,
)
from custom_components.ecostream.websocket_api import EcostreamWebsocket


def _make_ws(host="192.168.1.1"):
    hass = MagicMock()
    hass.loop.create_task = MagicMock(return_value=MagicMock())
    callback = AsyncMock()
    with patch(
        "custom_components.ecostream.websocket_api.async_get_clientsession",
        return_value=MagicMock(),
    ):
        ws = EcostreamWebsocket(
            hass=hass, host=host, message_callback=callback
        )
    return ws, hass, callback


def _get_create_task_mock(hass: MagicMock) -> MagicMock:
    return cast(MagicMock, hass.loop.create_task)


def _make_aiohttp_ws(messages=None, stop_ws=None):
    """Build a mock aiohttp WS connection that yields messages then stops."""
    mock_ws = AsyncMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)

    async def fake_aexit(exc_type, exc, tb):
        if stop_ws is not None:
            stop_ws._stopping = True
        return False

    mock_ws.__aexit__ = fake_aexit
    mock_ws.closed = False
    mock_ws.exception = MagicMock(return_value=None)

    msg_queue = list(messages or [])

    async def fake_receive():
        if msg_queue:
            msg = msg_queue.pop(0)
            if not msg_queue and stop_ws is not None:
                stop_ws._stopping = True
            return msg
        await asyncio.sleep(9999)

    mock_ws.receive = fake_receive
    return mock_ws


def _msg(msg_type, data=None):
    m = MagicMock()
    m.type = msg_type
    m.data = data
    return m


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_builds_ws_url():
    ws, _, _ = _make_ws("192.168.1.1")
    assert ws._ws_url == "ws://192.168.1.1/"


def test_init_strips_trailing_slash():
    ws, _, _ = _make_ws("192.168.1.1/")
    assert ws._ws_url == "ws://192.168.1.1/"


def test_init_default_state():
    ws, _, _ = _make_ws()
    assert ws._task is None
    assert ws._ws is None
    assert ws._stopping is False
    assert ws._has_received_payload is False
    assert ws._stale_logged is False


# ---------------------------------------------------------------------------
# async_start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_start_creates_task():
    ws, hass, _ = _make_ws()
    await ws.async_start()
    _get_create_task_mock(hass).assert_called_once()
    assert ws._stopping is False


@pytest.mark.asyncio
async def test_async_start_idempotent_when_task_running():
    ws, hass, _ = _make_ws()
    fake_task = MagicMock()
    fake_task.done = MagicMock(return_value=False)
    ws._task = fake_task
    await ws.async_start()
    _get_create_task_mock(hass).assert_not_called()


@pytest.mark.asyncio
async def test_async_start_restarts_when_task_done():
    ws, hass, _ = _make_ws()
    fake_task = MagicMock()
    fake_task.done = MagicMock(return_value=True)
    ws._task = fake_task
    await ws.async_start()
    _get_create_task_mock(hass).assert_called_once()


# ---------------------------------------------------------------------------
# async_disconnect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_disconnect_sets_stopping():
    ws, _, _ = _make_ws()
    ws._ws = None
    ws._task = None
    await ws.async_disconnect()
    assert ws._stopping is True


@pytest.mark.asyncio
async def test_async_disconnect_closes_ws():
    ws, _, _ = _make_ws()
    mock_ws = AsyncMock()
    ws._ws = mock_ws
    ws._task = None
    await ws.async_disconnect()
    mock_ws.close.assert_called_once()
    assert ws._task is None


@pytest.mark.asyncio
async def test_async_disconnect_cancels_task():
    ws, _, _ = _make_ws()
    ws._ws = None

    async def dummy():
        await asyncio.sleep(9999)

    task = asyncio.get_event_loop().create_task(dummy())
    ws._task = task
    await ws.async_disconnect()
    assert ws._task is None


@pytest.mark.asyncio
async def test_async_disconnect_handles_ws_close_error():
    ws, _, _ = _make_ws()
    mock_ws = AsyncMock()
    mock_ws.close = AsyncMock(side_effect=Exception("close error"))
    ws._ws = mock_ws
    ws._task = None
    await ws.async_disconnect()


# ---------------------------------------------------------------------------
# send_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_json_sends_payload():
    ws, _, _ = _make_ws()
    mock_ws = AsyncMock()
    ws._ws = mock_ws
    await ws.send_json({"key": "value"})
    mock_ws.send_json.assert_called_once_with({"key": "value"})


@pytest.mark.asyncio
async def test_send_json_no_ws_does_nothing():
    ws, _, _ = _make_ws()
    ws._ws = None
    await ws.send_json({"key": "value"})


@pytest.mark.asyncio
async def test_send_json_handles_exception():
    ws, _, _ = _make_ws()
    mock_ws = AsyncMock()
    mock_ws.send_json = AsyncMock(side_effect=Exception("send failed"))
    ws._ws = mock_ws
    await ws.send_json({"key": "value"})


# ---------------------------------------------------------------------------
# _handle_text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_text_valid_dict_calls_callback():
    ws, _, callback = _make_ws()
    await ws._handle_text('{"status": {"qset": 100}}')
    callback.assert_called_once_with({"status": {"qset": 100}})


@pytest.mark.asyncio
async def test_handle_text_invalid_json_ignored():
    ws, _, callback = _make_ws()
    await ws._handle_text("not json at all")
    callback.assert_not_called()


@pytest.mark.asyncio
async def test_handle_text_non_dict_json_ignored():
    ws, _, callback = _make_ws()
    await ws._handle_text("[1, 2, 3]")
    callback.assert_not_called()


@pytest.mark.asyncio
async def test_handle_text_callback_exception_handled():
    ws, _, callback = _make_ws()
    callback.side_effect = Exception("callback error")
    await ws._handle_text('{"key": "value"}')


# ---------------------------------------------------------------------------
# _send_heartbeat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_heartbeat_sends_empty_json():
    ws, _, _ = _make_ws()
    mock_ws = AsyncMock()
    ws._ws = mock_ws
    await ws._send_heartbeat()
    mock_ws.send_str.assert_called_once_with("{}")


@pytest.mark.asyncio
async def test_send_heartbeat_skipped_when_stopping():
    ws, _, _ = _make_ws()
    mock_ws = AsyncMock()
    ws._ws = mock_ws
    ws._stopping = True
    await ws._send_heartbeat()
    mock_ws.send_str.assert_not_called()


@pytest.mark.asyncio
async def test_send_heartbeat_skipped_when_no_ws():
    ws, _, _ = _make_ws()
    ws._ws = None
    await ws._send_heartbeat()


@pytest.mark.asyncio
async def test_send_heartbeat_handles_exception():
    ws, _, _ = _make_ws()
    mock_ws = AsyncMock()
    mock_ws.send_str = AsyncMock(
        side_effect=Exception("heartbeat failed")
    )
    ws._ws = mock_ws
    await ws._send_heartbeat()


# ---------------------------------------------------------------------------
# _check_stale
# ---------------------------------------------------------------------------


def test_check_stale_skipped_when_stopping():
    ws, hass, _ = _make_ws()
    ws._stopping = True
    ws._has_received_payload = True
    ws._ws = MagicMock()
    ws._last_message_ts = time.time() - 9999
    ws._check_stale()
    _get_create_task_mock(hass).assert_not_called()


def test_check_stale_skipped_before_first_payload():
    ws, hass, _ = _make_ws()
    ws._has_received_payload = False
    ws._ws = MagicMock()
    ws._last_message_ts = time.time() - 9999
    ws._check_stale()
    _get_create_task_mock(hass).assert_not_called()


def test_check_stale_skipped_when_no_ws():
    ws, _, _ = _make_ws()
    ws._has_received_payload = True
    ws._ws = None
    ws._last_message_ts = time.time() - 9999
    ws._check_stale()


def test_check_stale_skipped_when_fresh():
    ws, hass, _ = _make_ws()
    ws._has_received_payload = True
    ws._ws = MagicMock()
    ws._ws.closed = False
    ws._last_message_ts = time.time()
    ws._check_stale()
    _get_create_task_mock(hass).assert_not_called()


def test_check_stale_triggers_reconnect_when_stale():
    ws, hass, _ = _make_ws()
    ws._has_received_payload = True
    mock_ws = MagicMock()
    mock_ws.closed = False
    ws._ws = mock_ws
    ws._last_message_ts = time.time() - WS_STALE_TIMEOUT - 1
    ws._check_stale()
    _get_create_task_mock(hass).assert_called()
    assert ws._stale_logged is True


def test_check_stale_does_not_log_twice():
    ws, hass, _ = _make_ws()
    ws._has_received_payload = True
    mock_ws = MagicMock()
    mock_ws.closed = False
    ws._ws = mock_ws
    ws._last_message_ts = time.time() - WS_STALE_TIMEOUT - 1
    ws._stale_logged = True
    ws._check_stale()
    _get_create_task_mock(hass).assert_called()


def test_check_stale_skipped_when_ws_already_closed():
    ws, hass, _ = _make_ws()
    ws._has_received_payload = True
    mock_ws = MagicMock()
    mock_ws.closed = True
    ws._ws = mock_ws
    ws._last_message_ts = time.time() - WS_STALE_TIMEOUT - 1
    ws._check_stale()
    _get_create_task_mock(hass).assert_not_called()


# ---------------------------------------------------------------------------
# _run (integration-style)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_processes_text_message():
    ws, _, callback = _make_ws()

    aio_ws = _make_aiohttp_ws(
        [
            _msg(WSMsgType.TEXT, '{"status": {"qset": 100}}'),
            _msg(WSMsgType.CLOSE),
        ],
        stop_ws=ws,
    )
    ws._session.ws_connect = MagicMock(return_value=aio_ws)

    await ws._run()

    callback.assert_called_once_with({"status": {"qset": 100}})


@pytest.mark.asyncio
async def test_run_ignores_binary_message():
    ws, _, callback = _make_ws()

    aio_ws = _make_aiohttp_ws(
        [
            _msg(WSMsgType.BINARY),
            _msg(WSMsgType.CLOSE),
        ],
        stop_ws=ws,
    )
    ws._session.ws_connect = MagicMock(return_value=aio_ws)

    await ws._run()

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_run_breaks_on_close_message():
    ws, _, _ = _make_ws()

    aio_ws = _make_aiohttp_ws([_msg(WSMsgType.CLOSE)], stop_ws=ws)
    ws._session.ws_connect = MagicMock(return_value=aio_ws)

    await ws._run()


@pytest.mark.asyncio
async def test_run_breaks_on_closing_message():
    ws, _, _ = _make_ws()

    aio_ws = _make_aiohttp_ws([_msg(WSMsgType.CLOSING)], stop_ws=ws)
    ws._session.ws_connect = MagicMock(return_value=aio_ws)

    await ws._run()


@pytest.mark.asyncio
async def test_run_breaks_on_error_message():
    ws, _, _ = _make_ws()

    aio_ws = _make_aiohttp_ws([_msg(WSMsgType.ERROR)], stop_ws=ws)
    ws._session.ws_connect = MagicMock(return_value=aio_ws)

    await ws._run()


@pytest.mark.asyncio
async def test_run_handles_client_error_and_stops():
    ws, _, _ = _make_ws()
    ws._stopping = False

    call_count = 0

    def fake_connect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        ws._stopping = True
        raise ClientError("connection refused")

    ws._session.ws_connect = fake_connect

    with patch("asyncio.sleep", new=AsyncMock()):
        await ws._run()


@pytest.mark.asyncio
async def test_run_handles_unexpected_exception_and_stops():
    ws, _, _ = _make_ws()

    def fake_connect(*args, **kwargs):
        ws._stopping = True
        raise RuntimeError("unexpected")

    ws._session.ws_connect = fake_connect

    with patch("asyncio.sleep", new=AsyncMock()):
        await ws._run()


@pytest.mark.asyncio
async def test_run_sets_stopping_false_on_start():
    ws, _, _ = _make_ws()
    ws._stopping = False

    aio_ws = _make_aiohttp_ws([_msg(WSMsgType.CLOSE)], stop_ws=ws)
    ws._session.ws_connect = MagicMock(return_value=aio_ws)

    await ws._run()

    assert ws._ws is None


@pytest.mark.asyncio
async def test_run_resets_has_received_payload_on_reconnect():
    ws, _, _ = _make_ws()

    aio_ws = _make_aiohttp_ws([_msg(WSMsgType.CLOSE)], stop_ws=ws)
    ws._session.ws_connect = MagicMock(return_value=aio_ws)
    ws._has_received_payload = True

    await ws._run()
