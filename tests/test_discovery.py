from __future__ import annotations

from collections.abc import Coroutine, Sequence
from pathlib import Path
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from custom_components.ecostream.discovery import (
    async_process_dhcp,
    async_process_zeroconf,
)


def _make_hass(configured_hosts: Sequence[str] | None = None):
    hass = MagicMock()
    entries: list[MagicMock] = []
    for host in configured_hosts or []:
        entry = MagicMock()
        entry.data = {"host": host}
        entries.append(entry)
    hass.config_entries.async_entries.return_value = entries
    hass.config_entries.flow.async_init = AsyncMock()

    def _consume_task(coro: Coroutine[Any, Any, Any]) -> MagicMock:
        try:
            coro.close()
        except Exception:
            pass
        return MagicMock()

    hass.async_create_task = MagicMock(side_effect=_consume_task)
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
    ip_address = MagicMock()
    ip_address.__str__ = MagicMock(return_value="192.168.1.1")
    info.ip_address = ip_address
    await async_process_zeroconf(hass, info)
    hass.async_create_task.assert_not_called()


@pytest.mark.asyncio
async def test_zeroconf_starts_config_flow_for_new_device():
    hass = _make_hass()
    info = MagicMock()
    info.name = "EcoStream._tcp.local."
    ip_address = MagicMock()
    ip_address.__str__ = MagicMock(return_value="192.168.1.99")
    info.ip_address = ip_address
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
