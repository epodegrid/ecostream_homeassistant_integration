from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.core import HomeAssistant

from custom_components.ecostream.const import (
    DOMAIN,
    FAST_KEYS,
    FAST_MODE_SECONDS,
    SLOW_KEYS,
    SLOW_PUSH_INTERVAL,
)
from custom_components.ecostream.coordinator import (
    EcostreamDataUpdateCoordinator,
    RECONNECT_INTERVAL,
    RECONNECT_JITTER,
    RECONNECT_MIN_SLEEP,
)


def _make_coordinator(hass=None, host="192.168.1.1", options=None):
    """Helper to create a coordinator for testing."""
    if hass is None:
        hass = MagicMock(spec=HomeAssistant)
        hass.bus = MagicMock()
        hass.bus.async_listen_once = MagicMock()
        hass.data = {}  # Required for issue registry

    coordinator = EcostreamDataUpdateCoordinator(
        hass=hass,
        host=host,
        options=options or {},
    )

    return coordinator, hass


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_coordinator_initialization():
    coordinator, _ = _make_coordinator(host="192.168.1.100")

    assert coordinator.host == "192.168.1.100"
    assert coordinator.options == {}
    assert coordinator.data == {}
    assert coordinator.ws is None
    assert coordinator._started is False
    assert coordinator._stopping is False
    assert coordinator.boost_duration_minutes == 0
    assert coordinator.boost_remaining_seconds == 0


def test_coordinator_initialization_with_options():
    options = {"filter_replacement_days": 90, "boost_duration": 30}
    coordinator, _ = _make_coordinator(options=options)

    assert coordinator.options == options


def test_coordinator_push_intervals():
    coordinator, _ = _make_coordinator()

    assert coordinator._push_interval == float(SLOW_PUSH_INTERVAL)
    assert coordinator._fast_push_interval == int(FAST_MODE_SECONDS)


def test_coordinator_initial_timestamps():
    coordinator, _ = _make_coordinator()

    assert coordinator._last_push == 0.0
    assert coordinator._last_slow_push == 0.0
    assert coordinator._fast_mode_until == 0.0


# ---------------------------------------------------------------------------
# Lifecycle - async_start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_start_creates_websocket():
    coordinator, hass = _make_coordinator()

    with patch.object(
        coordinator, "_ensure_ws_started", new_callable=AsyncMock
    ) as mock_ensure:
        await coordinator.async_start()

        mock_ensure.assert_called_once()
        assert coordinator._started is True
        assert coordinator._stopping is False


@pytest.mark.asyncio
async def test_async_start_registers_event_listeners():
    coordinator, hass = _make_coordinator()

    with patch.object(
        coordinator, "_ensure_ws_started", new_callable=AsyncMock
    ):
        await coordinator.async_start()

        # Should register two event listeners
        assert hass.bus.async_listen_once.call_count == 2


@pytest.mark.asyncio
async def test_async_start_idempotent():
    coordinator, _ = _make_coordinator()

    with patch.object(
        coordinator, "_ensure_ws_started", new_callable=AsyncMock
    ) as mock_ensure:
        await coordinator.async_start()
        await coordinator.async_start()

        # Should only call once even if called twice
        mock_ensure.assert_called_once()


# ---------------------------------------------------------------------------
# Lifecycle - async_stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_stop_sets_stopping_flag():
    coordinator, _ = _make_coordinator()

    await coordinator.async_stop()

    assert coordinator._stopping is True


@pytest.mark.asyncio
async def test_async_stop_cancels_reconnect_task():
    coordinator, _ = _make_coordinator()

    mock_task = MagicMock()
    mock_task.cancel = MagicMock()
    coordinator._reconnect_task = mock_task

    with patch("asyncio.CancelledError", Exception):
        await coordinator.async_stop()

    mock_task.cancel.assert_called_once()
    assert coordinator._reconnect_task is None


@pytest.mark.asyncio
async def test_async_stop_disconnects_websocket():
    coordinator, _ = _make_coordinator()

    mock_ws = MagicMock()
    mock_ws.async_disconnect = AsyncMock()
    coordinator.ws = mock_ws

    await coordinator.async_stop()

    mock_ws.async_disconnect.assert_called_once()
    assert coordinator.ws is None


# ---------------------------------------------------------------------------
# WebSocket Management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_ws_started_creates_websocket():
    coordinator, _ = _make_coordinator()

    with patch(
        "custom_components.ecostream.coordinator.EcostreamWebsocket"
    ) as mock_ws_class:
        mock_ws_instance = MagicMock()
        mock_ws_instance.async_start = AsyncMock()
        mock_ws_class.return_value = mock_ws_instance

        await coordinator._ensure_ws_started()

        assert coordinator.ws is mock_ws_instance
        mock_ws_instance.async_start.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_ws_started_reuses_existing():
    coordinator, _ = _make_coordinator()

    mock_ws = MagicMock()
    mock_ws.async_start = AsyncMock()
    coordinator.ws = mock_ws

    await coordinator._ensure_ws_started()

    # Should reuse existing and call start again
    mock_ws.async_start.assert_called_once()


@pytest.mark.asyncio
async def test_force_ws_reconnect_creates_if_none():
    coordinator, _ = _make_coordinator()

    with patch.object(
        coordinator, "_ensure_ws_started", new_callable=AsyncMock
    ) as mock_ensure:
        await coordinator._force_ws_reconnect()

        mock_ensure.assert_called_once()


@pytest.mark.asyncio
async def test_force_ws_reconnect_disconnects_and_reconnects():
    coordinator, _ = _make_coordinator()

    mock_ws = MagicMock()
    mock_ws.async_disconnect = AsyncMock()
    mock_ws.async_start = AsyncMock()
    coordinator.ws = mock_ws
    coordinator._last_push = 123.45

    await coordinator._force_ws_reconnect()

    mock_ws.async_disconnect.assert_called_once()
    mock_ws.async_start.assert_called_once()
    assert coordinator._last_push == 0.0


@pytest.mark.asyncio
async def test_async_handle_hass_stop_calls_async_stop():
    coordinator, _ = _make_coordinator()
    with patch.object(
        coordinator, "async_stop", new=AsyncMock()
    ) as stop:
        await coordinator._async_handle_hass_stop(MagicMock())
    stop.assert_called_once()


@pytest.mark.asyncio
async def test_start_background_tasks_skips_when_existing():
    coordinator, _ = _make_coordinator()
    coordinator._reconnect_task = MagicMock()
    with patch("asyncio.create_task") as create_task:
        await coordinator._async_start_background_tasks(MagicMock())
    create_task.assert_not_called()


@pytest.mark.asyncio
async def test_start_background_tasks_creates_task():
    coordinator, _ = _make_coordinator()
    coordinator._reconnect_task = None
    fake_task = MagicMock()

    def _consume_task(coro, name=None):
        coro.close()
        return fake_task

    with patch(
        "asyncio.create_task", side_effect=_consume_task
    ) as create_task:
        await coordinator._async_start_background_tasks(MagicMock())
    create_task.assert_called_once()
    assert coordinator._reconnect_task is fake_task


@pytest.mark.asyncio
async def test_reconnect_loop_handles_cancelled_error():
    coordinator, _ = _make_coordinator()
    coordinator._stopping = False

    async def _raise_cancelled(_sleep_s):
        raise asyncio.CancelledError()

    with patch("asyncio.sleep", new=_raise_cancelled):
        with pytest.raises(asyncio.CancelledError):
            await coordinator._async_reconnect_loop()


@pytest.mark.asyncio
async def test_reconnect_loop_handles_generic_exception():
    coordinator, _ = _make_coordinator()
    coordinator._stopping = False

    async def _raise_error(_sleep_s):
        raise RuntimeError("boom")

    with patch("asyncio.sleep", new=_raise_error):
        await coordinator._async_reconnect_loop()


@pytest.mark.asyncio
async def test_reconnect_loop_calls_force_reconnect_once():
    coordinator, _ = _make_coordinator()
    coordinator._stopping = False
    coordinator._force_ws_reconnect = AsyncMock(
        side_effect=lambda: setattr(coordinator, "_stopping", True)
    )

    async def _noop_sleep(_sleep_s):
        return None

    with patch("asyncio.sleep", new=_noop_sleep):
        with patch("random.uniform", return_value=0):
            await coordinator._async_reconnect_loop()

    coordinator._force_ws_reconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_send_config_returns_false_without_ws():
    coordinator, _ = _make_coordinator()
    coordinator.ws = None
    ok = await coordinator.async_send_config({"x": 1}, "test")
    assert ok is False


@pytest.mark.asyncio
async def test_async_send_config_sends_payload_with_ws():
    coordinator, _ = _make_coordinator()
    coordinator.ws = MagicMock()
    coordinator.ws.send_json = AsyncMock()
    coordinator.mark_control_action = MagicMock()

    ok = await coordinator.async_send_config({"x": 1}, "test")

    assert ok is True
    coordinator.mark_control_action.assert_called_once()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"x": 1}}
    )


@pytest.mark.asyncio
async def test_async_send_config_marks_preset_restore_flag():
    coordinator, _ = _make_coordinator()
    coordinator.ws = MagicMock()
    coordinator.ws.send_json = AsyncMock()

    await coordinator.async_send_config(
        {"man_override_set_time": 600}, "preset mid"
    )

    assert coordinator._restore_schedule_after_override is True
    assert coordinator._last_override_active is True


@pytest.mark.asyncio
async def test_async_send_config_non_preset_override_disables_restore_flag():
    coordinator, _ = _make_coordinator()
    coordinator.ws = MagicMock()
    coordinator.ws.send_json = AsyncMock()

    await coordinator.async_send_config(
        {"man_override_set_time": 600}, "boost"
    )

    assert coordinator._restore_schedule_after_override is False
    assert coordinator._last_override_active is True


# ---------------------------------------------------------------------------
# Fast Mode
# ---------------------------------------------------------------------------


def test_mark_control_action_sets_fast_mode():
    coordinator, _ = _make_coordinator()

    with patch("time.time", return_value=1000.0):
        coordinator.mark_control_action()

    expected = 1000.0 + FAST_MODE_SECONDS
    assert coordinator._fast_mode_until == expected


# ---------------------------------------------------------------------------
# Message Handling - Basic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_ws_message_ignores_non_dict():
    coordinator, _ = _make_coordinator()

    await coordinator.handle_ws_message("not a dict")
    await coordinator.handle_ws_message(123)
    await coordinator.handle_ws_message(None)

    # Should not crash or change data
    assert coordinator.data == {}


@pytest.mark.asyncio
async def test_handle_ws_message_merges_payload():
    coordinator, _ = _make_coordinator()

    message = {"status": {"qset": 100}}

    with patch.object(
        coordinator, "async_set_updated_data"
    ) as mock_update:
        with patch.object(coordinator, "_update_filter_issue"):
            with patch("time.time", return_value=1000.0):
                await coordinator.handle_ws_message(message)

    assert "status" in coordinator.data
    assert coordinator.data["status"]["qset"] == 100


@pytest.mark.asyncio
async def test_handle_ws_message_triggers_push_on_first_message():
    coordinator, _ = _make_coordinator()
    coordinator._last_push = 0.0

    message = {"status": {"qset": 100}}

    with patch.object(
        coordinator, "async_set_updated_data"
    ) as mock_update:
        with patch.object(coordinator, "_update_filter_issue"):
            with patch("time.time", return_value=1000.0):
                await coordinator.handle_ws_message(message)

    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_handle_ws_message_fast_key_triggers_push():
    coordinator, _ = _make_coordinator()
    coordinator._last_push = 100.0

    # Fast key message after enough time
    message = {"status": {"qset": 200}}

    with patch.object(
        coordinator, "async_set_updated_data"
    ) as mock_update:
        with patch.object(coordinator, "_update_filter_issue"):
            with patch(
                "time.time", return_value=100.0 + SLOW_PUSH_INTERVAL + 1
            ):
                await coordinator.handle_ws_message(message)

    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_handle_ws_message_slow_key_respects_interval():
    coordinator, _ = _make_coordinator()
    coordinator._last_push = 100.0
    coordinator._last_slow_push = 100.0

    # Slow key message but not enough time passed
    message = {"config": {"setpoint_low": 90}}

    with patch.object(
        coordinator, "async_set_updated_data"
    ) as mock_update:
        with patch(
            "time.time", return_value=105.0
        ):  # Only 5 seconds passed
            await coordinator.handle_ws_message(message)

    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_handle_ws_message_slow_key_updates_snapshot_when_interval_passed():
    coordinator, _ = _make_coordinator()
    coordinator.data = {
        "config": {"setpoint_low": 90},
        "status": {"qset": 100},
    }
    coordinator._last_push = 100.0
    coordinator._last_slow_push = 100.0

    with patch.object(
        coordinator, "async_set_updated_data"
    ) as mock_update:
        with patch.object(coordinator, "_update_filter_issue"):
            with patch(
                "time.time", return_value=100.0 + SLOW_PUSH_INTERVAL + 1
            ):
                await coordinator.handle_ws_message(
                    {"config": {"setpoint_mid": 180}}
                )

    mock_update.assert_called_once()
    assert coordinator._last_slow_push > 100.0
    assert "config" in coordinator._last_slow_snapshot


@pytest.mark.asyncio
async def test_handle_ws_message_fast_mode_uses_shorter_interval():
    coordinator, _ = _make_coordinator()
    coordinator._last_push = 100.0
    coordinator._fast_mode_until = 200.0  # In fast mode

    message = {"status": {"qset": 150}}

    with patch.object(
        coordinator, "async_set_updated_data"
    ) as mock_update:
        with patch.object(coordinator, "_update_filter_issue"):
            # Fast interval (20s) passed, but not slow interval (10s default)
            with patch(
                "time.time", return_value=100.0 + FAST_MODE_SECONDS + 1
            ):
                await coordinator.handle_ws_message(message)

    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_handle_ws_message_preset_expiry_restores_schedule():
    coordinator, _ = _make_coordinator()
    coordinator._last_override_active = True
    coordinator._restore_schedule_after_override = True
    coordinator.data = {
        "config": {"schedule_enabled": False},
        "status": {"override_set_time_left": 10},
    }
    coordinator.async_send_config = AsyncMock(return_value=True)

    with patch.object(
        coordinator, "async_set_updated_data"
    ) as mock_update:
        with patch.object(coordinator, "_update_filter_issue"):
            with patch("time.time", return_value=1000.0):
                await coordinator.handle_ws_message(
                    {"status": {"override_set_time_left": 0}}
                )

    coordinator.async_send_config.assert_awaited_once_with(
        {"schedule_enabled": True},
        "schedule restore after preset",
    )
    assert coordinator._restore_schedule_after_override is False
    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_handle_ws_message_preset_expiry_skips_restore_when_schedule_on():
    coordinator, _ = _make_coordinator()
    coordinator._last_override_active = True
    coordinator._restore_schedule_after_override = True
    coordinator.data = {
        "config": {"schedule_enabled": True},
        "status": {"override_set_time_left": 10},
    }
    coordinator.async_send_config = AsyncMock(return_value=True)

    with patch.object(coordinator, "_update_filter_issue"):
        with patch("time.time", return_value=1000.0):
            await coordinator.handle_ws_message(
                {"status": {"override_set_time_left": 0}}
            )

    coordinator.async_send_config.assert_not_called()
    assert coordinator._restore_schedule_after_override is False


@pytest.mark.asyncio
async def test_preset_click_then_expiry_reenables_schedule_end_to_end():
    coordinator, _ = _make_coordinator()
    coordinator.ws = MagicMock()
    coordinator.ws.send_json = AsyncMock()
    coordinator.data = {
        "config": {"schedule_enabled": False},
        "status": {"override_set_time_left": 10},
    }

    # Simulate clicking a preset button.
    ok = await coordinator.async_send_config(
        {"man_override_set": 180, "man_override_set_time": 600},
        "preset mid",
    )
    assert ok is True
    coordinator.ws.send_json.reset_mock()

    with patch.object(coordinator, "_update_filter_issue"):
        with patch("time.time", return_value=1000.0):
            await coordinator.handle_ws_message(
                {"status": {"override_set_time_left": 0}}
            )

    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"schedule_enabled": True}}
    )
    assert coordinator._restore_schedule_after_override is False


# ---------------------------------------------------------------------------
# Merge Payload
# ---------------------------------------------------------------------------


def test_merge_payload_simple():
    coordinator, _ = _make_coordinator()

    coordinator._merge_payload({"a": 1, "b": 2})

    assert coordinator.data == {"a": 1, "b": 2}


def test_merge_payload_overwrites_simple_values():
    coordinator, _ = _make_coordinator()
    coordinator.data = {"a": 1, "b": 2}

    coordinator._merge_payload({"a": 10, "c": 3})

    assert coordinator.data == {"a": 10, "b": 2, "c": 3}


def test_merge_payload_deep_merges_dicts():
    coordinator, _ = _make_coordinator()
    coordinator.data = {
        "config": {"setpoint_low": 90, "setpoint_mid": 180}
    }

    coordinator._merge_payload({"config": {"setpoint_high": 270}})

    assert coordinator.data["config"]["setpoint_low"] == 90
    assert coordinator.data["config"]["setpoint_mid"] == 180
    assert coordinator.data["config"]["setpoint_high"] == 270


def test_merge_payload_replaces_non_dict_with_dict():
    coordinator, _ = _make_coordinator()
    coordinator.data = {"status": "connected"}

    coordinator._merge_payload({"status": {"qset": 100}})

    assert coordinator.data["status"] == {"qset": 100}


# ---------------------------------------------------------------------------
# Filter Issue Management
# ---------------------------------------------------------------------------


def test_update_filter_issue_creates_warning_when_overdue():
    coordinator, hass = _make_coordinator()
    coordinator.data = {"config": {"filter_datetime": 1000.0}}

    with patch(
        "time.time", return_value=2000.0
    ):  # Past the filter date
        with patch(
            "custom_components.ecostream.coordinator.ir"
        ) as mock_ir:
            coordinator._update_filter_issue()

            mock_ir.async_create_issue.assert_called_once()
            call_args = mock_ir.async_create_issue.call_args
            assert call_args[0][1] == DOMAIN
            assert call_args[0][2] == "filter_replacement_overdue"


def test_update_filter_issue_deletes_when_not_overdue():
    coordinator, hass = _make_coordinator()
    coordinator.data = {"config": {"filter_datetime": 2000.0}}

    with patch(
        "time.time", return_value=1000.0
    ):  # Before the filter date
        with patch(
            "custom_components.ecostream.coordinator.ir"
        ) as mock_ir:
            coordinator._update_filter_issue()

            mock_ir.async_delete_issue.assert_called_once()
            call_args = mock_ir.async_delete_issue.call_args
            assert call_args[0][1] == DOMAIN
            assert call_args[0][2] == "filter_replacement_overdue"


def test_update_filter_issue_deletes_when_no_filter_datetime():
    coordinator, hass = _make_coordinator()
    coordinator.data = {"config": {}}

    with patch("custom_components.ecostream.coordinator.ir") as mock_ir:
        coordinator._update_filter_issue()

        mock_ir.async_delete_issue.assert_called_once()


def test_update_filter_issue_deletes_when_filter_datetime_zero():
    coordinator, hass = _make_coordinator()
    coordinator.data = {"config": {"filter_datetime": 0}}

    with patch("custom_components.ecostream.coordinator.ir") as mock_ir:
        coordinator._update_filter_issue()

        mock_ir.async_delete_issue.assert_called_once()


# ---------------------------------------------------------------------------
# Fallback Update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_update_data_returns_current_data():
    coordinator, _ = _make_coordinator()
    coordinator.data = {"status": {"qset": 123}}

    result = await coordinator._async_update_data()

    assert result == {"status": {"qset": 123}}


# ---------------------------------------------------------------------------
# Reconnect Loop Constants
# ---------------------------------------------------------------------------


def test_reconnect_constants():
    """Test that constants are reasonable."""
    assert RECONNECT_INTERVAL == 3600  # 1 hour
    assert RECONNECT_JITTER == 300  # 5 minutes
    assert RECONNECT_MIN_SLEEP == 60  # 1 minute

    # Ensure min sleep is less than interval
    assert RECONNECT_MIN_SLEEP < RECONNECT_INTERVAL
    # Ensure jitter doesn't make sleep negative
    assert RECONNECT_INTERVAL - RECONNECT_JITTER > 0
