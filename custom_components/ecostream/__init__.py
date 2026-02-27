from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_PUSH_INTERVAL,
    DEFAULT_PUSH_INTERVAL,
    CONF_FAST_PUSH_INTERVAL,
    DEFAULT_FAST_PUSH_INTERVAL,
)
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """(Unused) configuration.yaml setup."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BUVA EcoStream from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host: str = entry.data[CONF_HOST]

    # Merge options
    options: dict[str, Any] = dict(entry.options or {})
    options.setdefault(CONF_PUSH_INTERVAL, DEFAULT_PUSH_INTERVAL)
    options.setdefault(CONF_FAST_PUSH_INTERVAL, DEFAULT_FAST_PUSH_INTERVAL)

    coordinator = EcostreamDataUpdateCoordinator(
        hass=hass,
        host=host,
        options=options,
    )

    # Start WebSocket listener
    await coordinator.async_start()

    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # ------------------------------------------
    # Platform loading (HA 2025+ API compatible)
    # ------------------------------------------
    if hasattr(hass.config_entries, "async_forward_entry_setups"):
        # New HA API (2025+)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        # Fallback for older HA versions
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_setup(entry, platform)
                for platform in PLATFORMS
            ]
        )

    _LOGGER.info(
        "EcoStream entry %s set up for host %s (push=%ss fast=%ss)",
        entry.entry_id,
        host,
        options.get(CONF_PUSH_INTERVAL),
        options.get(CONF_FAST_PUSH_INTERVAL),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload BUVA EcoStream config entry."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    # Stop WebSocket
    await coordinator.async_stop()

    # Platform unloading (HA 2025+ safe)
    if hasattr(hass.config_entries, "async_unload_platforms"):
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unload_results = await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ],
            return_exceptions=False,
        )
        unload_ok = all(unload_results)

    hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.info("EcoStream entry %s unloaded", entry.entry_id)

    return unload_ok
