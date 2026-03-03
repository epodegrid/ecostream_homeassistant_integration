from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from custom_components.ecostream.discovery import async_process_zeroconf, async_process_dhcp


def _make_hass(configured_hosts=None):
    hass = MagicMock()
    entries = []
    for host in (configured_hosts or []):
        entry = MagicMock()
        entry.data = {"host": host}
        entries.append(entry)
    hass.config_entries.async_entries.return_value = entries
    hass.config_entries.flow.async_init = AsyncMock()
    hass.async_create_task = MagicMock()
    return hass


# ---------------------------------------------------------------------------
# async_process_zeroconf
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zeroconf_ignores_non_ecostream_name():
    hass = _make_hass()
    info = MagicMock()
    info.name = "SomeOtherDevice"
    info.ip_address = "192.168.1.1"
    await async_process_zeroconf(hass, info)
    hass.async_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_zeroconf_ignores_missing_ip():
    hass = _make_hass()
    info = MagicMock()
    info.name = "EcoStream._tcp.local."
    info.ip_address = None
    await async_process_zeroconf(hass, info)
    hass.async_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_zeroconf_skips_already_configured():
    hass = _make_hass(configured_hosts=["192.168.1.1"])
    info = MagicMock()
    info.name = "EcoStream._tcp.local."
    info.ip_address = MagicMock(__str__=lambda self: "192.168.1.1")
    await async_process_zeroconf(hass, info)
    hass.async_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_zeroconf_starts_config_flow_for_new_device():
    hass = _make_hass()
    info = MagicMock()
    info.name = "EcoStream._tcp.local."
    info.ip_address = MagicMock(__str__=lambda self: "192.168.1.99")
    await async_process_zeroconf(hass, info)
    hass.async_create_task.assert_called_once()


# ---------------------------------------------------------------------------
# async_process_dhcp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dhcp_ignores_non_ecostream_hostname():
    hass = _make_hass()
    info = MagicMock()
    info.hostname = "some-other-device"
    info.ip = "192.168.1.1"
    await async_process_dhcp(hass, info)
    hass.async_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_dhcp_ignores_missing_ip():
    hass = _make_hass()
    info = MagicMock()
    info.hostname = "ecostream-abc"
    info.ip = None
    await async_process_dhcp(hass, info)
    hass.async_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_dhcp_skips_already_configured():
    hass = _make_hass(configured_hosts=["192.168.1.1"])
    info = MagicMock()
    info.hostname = "ecostream-abc"
    info.ip = "192.168.1.1"
    await async_process_dhcp(hass, info)
    hass.async_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_dhcp_starts_config_flow_for_new_device():
    hass = _make_hass()
    info = MagicMock()
    info.hostname = "ecostream-abc"
    info.ip = "192.168.1.99"
    await async_process_dhcp(hass, info)
    hass.async_create_task.assert_called_once()