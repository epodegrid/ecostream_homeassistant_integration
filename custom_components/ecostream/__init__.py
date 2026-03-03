from __future__ import annotations

import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
import logging
from typing import Any

from aiohttp import ClientError, WSMsgType

from .const import (
    CONF_FAST_PUSH_INTERVAL,
    CONF_PUSH_INTERVAL,
    DEFAULT_FAST_PUSH_INTERVAL,
    DEFAULT_PUSH_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def _probe_host(hass: HomeAssistant, host: str) -> None:
    """Try a single WebSocket receive to verify the device is reachable."""
    session = async_get_clientsession(hass)
    url = f"http://{host}/" if "://" not in host else f"{host}/"
    try:
        async with session.ws_connect(url, heartbeat=None) as ws:
            msg = await ws.receive(timeout=5)
            if msg.type not in (WSMsgType.TEXT, WSMsgType.BINARY):
                raise ConfigEntryNotReady(
                    f"Unexpected WebSocket message type: {msg.type}"
                )
    except ConfigEntryNotReady:
        raise
    except (TimeoutError, ClientError) as err:
        raise ConfigEntryNotReady(
            f"Cannot connect to EcoStream at {host}: {err}"
        ) from err
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Unexpected error connecting to EcoStream at {host}: {err}"
        ) from err


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """(Unused) configuration.yaml setup."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up BUVA EcoStream from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host: str = entry.data[CONF_HOST]

    await _probe_host(hass, host)

    # Merge options
    options: dict[str, Any] = dict(entry.options or {})
    options.setdefault(CONF_PUSH_INTERVAL, DEFAULT_PUSH_INTERVAL)
    options.setdefault(
        CONF_FAST_PUSH_INTERVAL, DEFAULT_FAST_PUSH_INTERVAL
    )

    coordinator = EcostreamDataUpdateCoordinator(
        hass=hass,
        host=host,
        options=options,
    )

    # Start WebSocket listener
    await coordinator.async_start()

    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    _LOGGER.info(
        "EcoStream entry %s set up for host %s (push=%ss fast=%ss)",
        entry.entry_id,
        host,
        options.get(CONF_PUSH_INTERVAL),
        options.get(CONF_FAST_PUSH_INTERVAL),
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload BUVA EcoStream config entry."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    # Stop WebSocket
    await coordinator.async_stop()

    # Platform unloading (HA 2025+ safe)
    if hasattr(hass.config_entries, "async_unload_platforms"):
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        )
    else:
        unload_results = await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(
                    entry, platform
                )
                for platform in PLATFORMS
            ],
            return_exceptions=False,
        )
        unload_ok = all(unload_results)

    hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.info("EcoStream entry %s unloaded", entry.entry_id)

    return unload_ok
