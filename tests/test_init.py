from __future__ import annotations

from homeassistant.exceptions import ConfigEntryNotReady
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError, WSMsgType
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from custom_components.ecostream import (
    _probe_host,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ecostream.const import (
    CONF_FAST_PUSH_INTERVAL,
    CONF_PUSH_INTERVAL,
    DOMAIN,
)


def _make_ws_session(msg_type=WSMsgType.TEXT, side_effect=None):
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
        await _probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_binary_message_success():
    hass = MagicMock()
    session = _make_ws_session(WSMsgType.BINARY)
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        await _probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_unexpected_ws_type_raises():
    hass = MagicMock()
    session = _make_ws_session(WSMsgType.ERROR)
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await _probe_host(hass, "192.168.1.1")


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
            await _probe_host(hass, "192.168.1.1")


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
            await _probe_host(hass, "192.168.1.1")


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
            await _probe_host(hass, "192.168.1.1")


@pytest.mark.asyncio
async def test_probe_host_adds_scheme_if_missing():
    hass = MagicMock()
    session = _make_ws_session(WSMsgType.TEXT)
    with patch(
        "custom_components.ecostream.async_get_clientsession",
        return_value=session,
    ):
        await _probe_host(hass, "192.168.1.1")
    call_url = session.ws_connect.call_args[0][0]
    assert call_url.startswith("http://")


# ---------------------------------------------------------------------------
# async_setup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_setup_returns_true():
    assert await async_setup(MagicMock(), {}) is True


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
    entry.options = {CONF_PUSH_INTERVAL: 60, CONF_FAST_PUSH_INTERVAL: 5}

    mock_coordinator = MagicMock()
    mock_coordinator.async_start = AsyncMock()

    with patch(
        "custom_components.ecostream._probe_host", new=AsyncMock()
    ):
        with patch(
            "custom_components.ecostream.EcostreamDataUpdateCoordinator",
            return_value=mock_coordinator,
        ):
            result = await async_setup_entry(hass, entry)

    assert result is True
    assert DOMAIN in hass.data
    assert "test_entry" in hass.data[DOMAIN]
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
            "custom_components.ecostream.EcostreamDataUpdateCoordinator",
            return_value=mock_coordinator,
        ) as mock_cls:
            await async_setup_entry(hass, entry)
            _, kwargs = mock_cls.call_args
            assert CONF_PUSH_INTERVAL in kwargs["options"]
            assert CONF_FAST_PUSH_INTERVAL in kwargs["options"]


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
    hass.data = {DOMAIN: {"test_entry": MagicMock()}}
    hass.config_entries.async_unload_platforms = AsyncMock(
        return_value=True
    )

    coordinator = MagicMock()
    coordinator.async_stop = AsyncMock()

    entry = MagicMock()

    entry.entry_id = "test_entry"
    entry.runtime_data = coordinator

    await async_unload_entry(hass, entry)
    assert "test_entry" not in hass.data[DOMAIN]
