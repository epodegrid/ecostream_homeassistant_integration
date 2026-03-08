from __future__ import annotations

import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import (
    async_get as async_get_device_registry,
)
import logging
import time
from typing import Any

from aiohttp import ClientError, WSMsgType

from .const import (
    CONF_ALLOW_OVERRIDE_FILTER_DATE,
    CONF_BOOST_DURATION,
    CONF_FILTER_REPLACEMENT_DAYS,
    CONF_PRESET_OVERRIDE_MINUTES,
    DEFAULT_BOOST_DURATION_MINUTES,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
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
                    translation_domain=DOMAIN,
                    translation_key="cannot_connect",
                    translation_placeholders={"host": host},
                )
    except ConfigEntryNotReady:
        raise
    except (TimeoutError, ClientError) as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"host": host},
        ) from err
    except Exception as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="unknown_error",
            translation_placeholders={"host": host},
        ) from err


async def _cleanup_stale_devices(
    hass: HomeAssistant, entry: ConfigEntry, current_host: str
) -> None:
    """Remove devices whose identifier host no longer matches the current host."""
    dev_reg = async_get_device_registry(hass)
    for device in list(dev_reg.devices.values()):
        for config_entry_id in device.config_entries:
            if config_entry_id != entry.entry_id:
                continue
            stale = any(
                identifier[0] == DOMAIN
                and identifier[1] != current_host
                for identifier in device.identifiers
            )
            if stale:
                _LOGGER.debug(
                    "Removing stale EcoStream device %s (old host identifier)",
                    device.id,
                )
                dev_reg.async_remove_device(device.id)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up BUVA EcoStream from a config entry."""

    host: str = entry.data[CONF_HOST]

    await _probe_host(hass, host)
    await _cleanup_stale_devices(hass, entry, host)

    # Merge options
    options: dict[str, Any] = dict(entry.options or {})
    options.setdefault(
        CONF_FILTER_REPLACEMENT_DAYS, DEFAULT_FILTER_REPLACEMENT_DAYS
    )
    options.setdefault(
        CONF_PRESET_OVERRIDE_MINUTES, DEFAULT_PRESET_OVERRIDE_MINUTES
    )
    options.setdefault(
        CONF_BOOST_DURATION, DEFAULT_BOOST_DURATION_MINUTES
    )

    coordinator = EcostreamDataUpdateCoordinator(
        hass=hass,
        host=host,
        options=options,
    )

    # Start WebSocket listener
    await coordinator.async_start()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    entry.async_on_unload(
        entry.add_update_listener(_async_options_updated)
    )

    _LOGGER.info(
        "EcoStream entry %s set up for host %s (filter_days=%s preset_override=%sm boost=%sm)",
        entry.entry_id,
        host,
        options.get(CONF_FILTER_REPLACEMENT_DAYS),
        options.get(CONF_PRESET_OVERRIDE_MINUTES),
        options.get(CONF_BOOST_DURATION),
    )

    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Update device configuration when options change."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    # Update boost duration
    boost_duration = int(
        entry.options.get(
            CONF_BOOST_DURATION, DEFAULT_BOOST_DURATION_MINUTES
        )
    )
    coordinator.boost_duration_minutes = boost_duration

    # Only update filter date if override is allowed
    allow_override = entry.options.get(
        CONF_ALLOW_OVERRIDE_FILTER_DATE, False
    )

    if allow_override:
        if not coordinator.ws:
            _LOGGER.debug(
                "EcoStream options updated locally (boost_duration=%sm), skipping filter_datetime update because WS is disconnected",
                boost_duration,
            )
            return

        filter_days = int(
            entry.options.get(
                CONF_FILTER_REPLACEMENT_DAYS,
                DEFAULT_FILTER_REPLACEMENT_DAYS,
            )
        )
        filter_datetime = int(time.time() + filter_days * 86400)

        await coordinator.ws.send_json(
            {"config": {"filter_datetime": filter_datetime}}
        )
        _LOGGER.debug(
            "EcoStream filter_datetime updated: %s days → timestamp %s, boost_duration=%sm",
            filter_days,
            filter_datetime,
            boost_duration,
        )
    else:
        _LOGGER.debug(
            "EcoStream options updated: boost_duration=%sm (filter override disabled)",
            boost_duration,
        )


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

    _LOGGER.info("EcoStream entry %s unloaded", entry.entry_id)

    return unload_ok
