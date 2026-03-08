from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import time
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from custom_components.ecostream.const import (
    CONF_FAST_PUSH_INTERVAL,
    CONF_PUSH_INTERVAL,
    DEFAULT_FAST_PUSH_INTERVAL,
    DEFAULT_PUSH_INTERVAL,
    FAST_MODE_SECONDS,
)
from custom_components.ecostream.coordinator import (
    EcostreamDataUpdateCoordinator,
)


def _make_coordinator(data=None, options=None):
    hass = MagicMock()
    hass.bus.async_listen_once = MagicMock()
    with patch.object(
        DataUpdateCoordinator, "__init__", return_value=None
    ):
        coord = EcostreamDataUpdateCoordinator(
            hass=hass, host="192.168.1.1", options=options
        )
    coord.hass = hass
    coord.data = data or {}
    coord.async_set_updated_data = MagicMock()
    return coord


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_defaults():
    coord = _make_coordinator()
    assert coord.host == "192.168.1.1"
    assert coord._push_interval == float(DEFAULT_PUSH_INTERVAL)
    assert coord._fast_push_interval == float(
        DEFAULT_FAST_PUSH_INTERVAL
    )
    assert coord._last_push == 0.0
    assert coord._started is False
    assert coord._stopping is False
    assert coord.boost_duration_minutes == 0


def test_init_custom_options():
    coord = _make_coordinator(
        options={CONF_PUSH_INTERVAL: 60, CONF_FAST_PUSH_INTERVAL: 5}
    )
    assert coord._push_interval == 60.0
    assert coord._fast_push_interval == 5.0


# ---------------------------------------------------------------------------
# _merge_payload
# ---------------------------------------------------------------------------


def test_merge_payload_simple():
    coord = _make_coordinator()
    coord._merge_payload({"key": "value"})
    assert coord.data["key"] == "value"


def test_merge_payload_nested_dict_merges():
    coord = _make_coordinator(data={"status": {"a": 1}})
    coord._merge_payload({"status": {"b": 2}})
    assert coord.data["status"] == {"a": 1, "b": 2}


def test_merge_payload_nested_overwrites_existing_key():
    coord = _make_coordinator(data={"status": {"a": 1, "b": 2}})
    coord._merge_payload({"status": {"a": 99}})
    assert coord.data["status"]["a"] == 99
    assert coord.data["status"]["b"] == 2


def test_merge_payload_replaces_non_dict_with_value():
    coord = _make_coordinator(data={"key": "old"})
    coord._merge_payload({"key": "new"})
    assert coord.data["key"] == "new"


# ---------------------------------------------------------------------------
# mark_control_action
# ---------------------------------------------------------------------------


def test_mark_control_action_sets_fast_mode():
    coord = _make_coordinator()
    before = time.time()
    coord.mark_control_action()
    assert coord._fast_mode_until >= before + FAST_MODE_SECONDS - 0.1


# ---------------------------------------------------------------------------
# handle_ws_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_ws_message_ignores_non_dict():
    coord = _make_coordinator()
    await coord.handle_ws_message("not a dict")  # type: ignore[arg-type]
    cast(MagicMock, coord.async_set_updated_data).assert_not_called()


@pytest.mark.asyncio
async def test_handle_ws_message_first_push_always_fires():
    coord = _make_coordinator()
    coord._last_push = 0
    await coord.handle_ws_message({"status": {"qset": 100}})
    cast(MagicMock, coord.async_set_updated_data).assert_called_once()


@pytest.mark.asyncio
async def test_handle_ws_message_throttles_when_too_soon():
    coord = _make_coordinator()
    coord._last_push = time.time()
    coord._push_interval = 9999
    await coord.handle_ws_message({"status": {"qset": 100}})
    cast(MagicMock, coord.async_set_updated_data).assert_not_called()


@pytest.mark.asyncio
async def test_handle_ws_message_fires_when_interval_elapsed():
    coord = _make_coordinator()
    coord._last_push = time.time() - 9999
    await coord.handle_ws_message({"status": {"qset": 100}})
    cast(MagicMock, coord.async_set_updated_data).assert_called_once()


@pytest.mark.asyncio
async def test_handle_ws_message_slow_key_updates_snapshot():
    coord = _make_coordinator()
    coord._last_push = 0
    await coord.handle_ws_message({"config": {"capacity_max": 350}})
    assert coord._last_slow_push > 0


@pytest.mark.asyncio
async def test_handle_ws_message_fast_mode_uses_fast_interval():
    coord = _make_coordinator()
    coord._fast_mode_until = time.time() + 9999
    coord._fast_push_interval = 0.0
    coord._last_push = time.time() - 1
    await coord.handle_ws_message({"status": {"qset": 100}})
    cast(MagicMock, coord.async_set_updated_data).assert_called_once()


# ---------------------------------------------------------------------------
# async_stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_stop_sets_stopping():
    coord = _make_coordinator()
    coord.ws = None
    await coord.async_stop()
    assert coord._stopping is True


@pytest.mark.asyncio
async def test_async_stop_disconnects_ws():
    coord = _make_coordinator()
    ws = MagicMock()
    ws.async_disconnect = AsyncMock()
    coord.ws = ws
    await coord.async_stop()
    ws.async_disconnect.assert_called_once()
    assert coord.ws is None


@pytest.mark.asyncio
async def test_async_stop_cancels_reconnect_task():
    coord = _make_coordinator()
    coord.ws = None

    async def dummy():
        await asyncio.sleep(9999)

    real_task = asyncio.get_event_loop().create_task(dummy())
    coord._reconnect_task = real_task
    await coord.async_stop()
    assert coord._reconnect_task is None


# ---------------------------------------------------------------------------
# async_start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_start_idempotent():
    coord = _make_coordinator()
    coord._started = True
    coord._ensure_ws_started = AsyncMock()
    await coord.async_start()
    coord._ensure_ws_started.assert_not_called()


@pytest.mark.asyncio
async def test_async_start_registers_listeners():
    coord = _make_coordinator()
    coord._ensure_ws_started = AsyncMock()
    await coord.async_start()
    assert (
        cast(MagicMock, coord.hass.bus.async_listen_once).call_count
        == 2
    )
    assert coord._started is True


# ---------------------------------------------------------------------------
# _force_ws_reconnect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_force_ws_reconnect_no_ws_calls_ensure():
    coord = _make_coordinator()
    coord.ws = None
    coord._ensure_ws_started = AsyncMock()
    await coord._force_ws_reconnect()
    coord._ensure_ws_started.assert_called_once()


@pytest.mark.asyncio
async def test_force_ws_reconnect_with_ws_reconnects():
    coord = _make_coordinator()
    ws = MagicMock()
    ws.async_disconnect = AsyncMock()
    ws.async_start = AsyncMock()
    coord.ws = ws
    coord._last_push = 999.0
    await coord._force_ws_reconnect()
    ws.async_disconnect.assert_called_once()
    ws.async_start.assert_called_once()
    assert coord._last_push == 0.0


# ---------------------------------------------------------------------------
# _async_start_background_tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_background_tasks_idempotent():
    coord = _make_coordinator()
    existing = MagicMock()
    coord._reconnect_task = existing
    await coord._async_start_background_tasks(None)
    assert coord._reconnect_task is existing


@pytest.mark.asyncio
async def test_start_background_tasks_creates_task():
    coord = _make_coordinator()
    coord._reconnect_task = None
    coord._stopping = True
    with patch("asyncio.create_task") as mock_create:
        mock_create.return_value = MagicMock()
        await coord._async_start_background_tasks(None)
        mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# _async_update_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_update_data_returns_data():
    coord = _make_coordinator(data={"key": "val"})
    result = await coord._async_update_data()
    assert result == {"key": "val"}


@pytest.mark.asyncio
async def test_coordinator_update_timeout(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator handles timeout errors."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.ecostream.coordinator.EcostreamApiClient"
    ) as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.async_get_data.side_effect = asyncio.TimeoutError(
            "Timeout"
        )

        await hass.config_entries.async_setup(
            mock_config_entry.entry_id
        )
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Coordinator should handle timeout gracefully
        assert coordinator.last_update_success is False
