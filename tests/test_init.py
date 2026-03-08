from __future__ import annotations

from homeassistant.exceptions import ConfigEntryNotReady
from pathlib import Path
import sys
from typing import Final, cast
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError, WSMsgType
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import custom_components.ecostream as ecostream
from custom_components.ecostream import (
    async_setup_entry,
    async_unload_entry,
    const as ecostream_const,
)

DOMAIN: Final[str] = cast(str, ecostream_const.DOMAIN)
probe_host = getattr(ecostream, "_probe_host")


def _make_ws_session(
    msg_type: WSMsgType = WSMsgType.TEXT,
    side_effect: Exception | None = None,
):
    mock_ws = AsyncMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)
    if side_effect:
        mock_ws.receive = AsyncMock(side_effect=side_effect)
    else:
        msg = MagicMock()
        msg.type = msg_type
        mock_ws.receive = AsyncMock(return_value=msg)
    session = MagicMock()
    session.ws_connect = MagicMock(return_value=mock_ws)
    return session


# ---------------------------------------------------------------------------
# _probe_host
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_probe_host_success():
    hass = MagicMock()
    session = _make_ws_session(WSMsgType.TEXT)
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        await probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_binary_message_success():
    hass = MagicMock()
    session = _make_ws_session(WSMsgType.BINARY)
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        await probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_unexpected_ws_type_raises():
    hass = MagicMock()
    session = _make_ws_session(WSMsgType.ERROR)
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_client_error_raises():
    hass = MagicMock()
    session = MagicMock()
    session.ws_connect = MagicMock(side_effect=ClientError("fail"))
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_timeout_raises():
    hass = MagicMock()
    session = MagicMock()
    session.ws_connect = MagicMock(side_effect=TimeoutError())
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_unexpected_exception_raises():
    hass = MagicMock()
    session = MagicMock()
    session.ws_connect = MagicMock(
        side_effect=RuntimeError("unexpected")
    )
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_adds_scheme_if_missing():
    hass = MagicMock()
    session = _make_ws_session(WSMsgType.TEXT)
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        await probe_host(hass, "192.168.1.1")
    call_url = session.ws_connect.call_args[0][0]
    assert call_url.startswith("http://")


# ---------------------------------------------------------------------------
# async_setup
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_setup_entry_success():
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock(
        return_value=True
    )

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"host": "192.168.1.1"}
    entry.options = {
        "filter_replacement_days": 180,
        "preset_override_minutes": 60,
        "boost_duration": 15,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.async_start = AsyncMock()

    with patch(
        "custom_components.ecostream._probe_host", new=AsyncMock()
    ):
        with patch(
            "custom_components.ecostream._cleanup_stale_devices",
            new=AsyncMock(),
        ):
            with patch(
                "custom_components.ecostream.EcostreamDataUpdateCoordinator",
                return_value=mock_coordinator,
            ):
                result = await async_setup_entry(hass, entry)

    assert result is True
    assert entry.runtime_data == mock_coordinator
    mock_coordinator.async_start.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_uses_default_options():
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock(
        return_value=True
    )

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"host": "192.168.1.1"}
    entry.options = {}

    mock_coordinator = MagicMock()
    mock_coordinator.async_start = AsyncMock()

    with patch(
        "custom_components.ecostream._probe_host", new=AsyncMock()
    ):
        with patch(
            "custom_components.ecostream._cleanup_stale_devices",
            new=AsyncMock(),
        ):
            with patch(
                "custom_components.ecostream.EcostreamDataUpdateCoordinator",
                return_value=mock_coordinator,
            ) as mock_cls:
                await async_setup_entry(hass, entry)
                _, kwargs = mock_cls.call_args
                # Check that default options are set
                assert "filter_replacement_days" in kwargs["options"]
                assert "preset_override_minutes" in kwargs["options"]
                assert "boost_duration" in kwargs["options"]


# ---------------------------------------------------------------------------
# async_unload_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_unload_entry_success():
    hass = MagicMock()
    hass.data = {DOMAIN: {"test_entry": MagicMock()}}
    hass.config_entries.async_unload_platforms = AsyncMock(
        return_value=True
    )

    coordinator = MagicMock()
    coordinator.async_stop = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.runtime_data = coordinator

    result = await async_unload_entry(hass, entry)
    coordinator.async_stop.assert_called_once()
    assert result is True


@pytest.mark.asyncio
async def test_async_unload_entry_removes_from_data():
    hass = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(
        return_value=True
    )

    coordinator = MagicMock()
    coordinator.async_stop = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.runtime_data = coordinator

    result = await async_unload_entry(hass, entry)
    assert result is True
    coordinator.async_stop.assert_called_once()


# ---------------------------------------------------------------------------
# _cleanup_stale_devices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_stale_devices_removes_old_host():
    """Test that devices with old host identifiers are removed."""
    from custom_components.ecostream import _cleanup_stale_devices
    from homeassistant.helpers.device_registry import DeviceRegistry

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    current_host = "192.168.1.100"

    # Create mock device with old host identifier
    old_device = MagicMock()
    old_device.id = "old_device_id"
    old_device.config_entries = {"test_entry"}
    old_device.identifiers = {(DOMAIN, "192.168.1.1")}

    # Create mock device with current host identifier
    current_device = MagicMock()
    current_device.id = "current_device_id"
    current_device.config_entries = {"test_entry"}
    current_device.identifiers = {(DOMAIN, "192.168.1.100")}

    # Create mock device from different config entry
    other_device = MagicMock()
    other_device.id = "other_device_id"
    other_device.config_entries = {"other_entry"}
    other_device.identifiers = {(DOMAIN, "192.168.1.1")}

    mock_dev_reg = MagicMock(spec=DeviceRegistry)
    mock_dev_reg.devices = {
        "old": old_device,
        "current": current_device,
        "other": other_device,
    }
    mock_dev_reg.async_remove_device = MagicMock()

    with patch(
        "custom_components.ecostream.async_get_device_registry",
        return_value=mock_dev_reg,
    ):
        await _cleanup_stale_devices(hass, entry, current_host)

    # Old device should be removed
    mock_dev_reg.async_remove_device.assert_called_once_with(
        "old_device_id"
    )


@pytest.mark.asyncio
async def test_cleanup_stale_devices_keeps_current_host():
    """Test that devices with current host are not removed."""
    from custom_components.ecostream import _cleanup_stale_devices
    from homeassistant.helpers.device_registry import DeviceRegistry

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    current_host = "192.168.1.100"

    current_device = MagicMock()
    current_device.id = "current_device_id"
    current_device.config_entries = {"test_entry"}
    current_device.identifiers = {(DOMAIN, "192.168.1.100")}

    mock_dev_reg = MagicMock(spec=DeviceRegistry)
    mock_dev_reg.devices = {"current": current_device}
    mock_dev_reg.async_remove_device = MagicMock()

    with patch(
        "custom_components.ecostream.async_get_device_registry",
        return_value=mock_dev_reg,
    ):
        await _cleanup_stale_devices(hass, entry, current_host)

    # Should not remove any devices
    mock_dev_reg.async_remove_device.assert_not_called()


# ---------------------------------------------------------------------------
# _async_options_updated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_options_updated_with_filter_override_enabled():
    """Test options update when filter override is enabled."""
    from custom_components.ecostream import _async_options_updated

    hass = MagicMock()
    entry = MagicMock()
    entry.options = {
        "boost_duration": 30,
        "allow_override_filter_date": True,
        "filter_replacement_days": 90,
    }

    coordinator = MagicMock()
    coordinator.ws = MagicMock()
    coordinator.ws.send_json = AsyncMock()
    entry.runtime_data = coordinator

    with patch(
        "custom_components.ecostream.time.time", return_value=1000
    ):
        await _async_options_updated(hass, entry)

    assert coordinator.boost_duration_minutes == 30
    coordinator.ws.send_json.assert_called_once()
    call_args = coordinator.ws.send_json.call_args[0][0]
    assert "config" in call_args
    assert "filter_datetime" in call_args["config"]
    expected_timestamp = 1000 + (90 * 86400)
    assert call_args["config"]["filter_datetime"] == expected_timestamp


@pytest.mark.asyncio
async def test_options_updated_with_filter_override_disabled():
    """Test options update when filter override is disabled."""
    from custom_components.ecostream import _async_options_updated

    hass = MagicMock()
    entry = MagicMock()
    entry.options = {
        "boost_duration": 15,
        "allow_override_filter_date": False,
    }

    coordinator = MagicMock()
    coordinator.ws = MagicMock()
    coordinator.ws.send_json = AsyncMock()
    entry.runtime_data = coordinator

    await _async_options_updated(hass, entry)

    assert coordinator.boost_duration_minutes == 15
    # Should not send JSON when override is disabled
    coordinator.ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_options_updated_with_ws_disconnected():
    """Test options update when WebSocket is disconnected."""
    from custom_components.ecostream import _async_options_updated

    hass = MagicMock()
    entry = MagicMock()
    entry.options = {
        "boost_duration": 20,
        "allow_override_filter_date": True,
        "filter_replacement_days": 180,
    }

    coordinator = MagicMock()
    coordinator.ws = None  # Disconnected
    entry.runtime_data = coordinator

    await _async_options_updated(hass, entry)

    assert coordinator.boost_duration_minutes == 20
    # No exception should be raised


@pytest.mark.asyncio
async def test_options_updated_uses_defaults():
    """Test options update with default values."""
    from custom_components.ecostream import _async_options_updated

    hass = MagicMock()
    entry = MagicMock()
    entry.options = {}  # No options set

    coordinator = MagicMock()
    coordinator.ws = None
    entry.runtime_data = coordinator

    await _async_options_updated(hass, entry)

    # Should use default boost duration (15 minutes)
    assert coordinator.boost_duration_minutes == 15


# ---------------------------------------------------------------------------
# async_unload_entry (legacy HA versions)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_unload_entry_legacy_ha_version():
    """Test unload entry for older HA versions without async_unload_platforms."""
    hass = MagicMock()
    hass.config_entries.async_forward_entry_unload = AsyncMock(
        return_value=True
    )
    # Remove async_unload_platforms to simulate old HA version
    if hasattr(hass.config_entries, "async_unload_platforms"):
        delattr(hass.config_entries, "async_unload_platforms")

    coordinator = MagicMock()
    coordinator.async_stop = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.runtime_data = coordinator

    result = await async_unload_entry(hass, entry)

    assert result is True
    coordinator.async_stop.assert_called_once()
    # Verify that async_forward_entry_unload was called for each platform
    assert (
        hass.config_entries.async_forward_entry_unload.call_count == 5
    )
