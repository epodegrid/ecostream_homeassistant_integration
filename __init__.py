"""The ecostream integration."""

from __future__ import annotations

import asyncio
import json

import logging

from websocket import create_connection

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import service

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]


class MyApi:
    def __init__(self):
        self.connection = None
        self._data = None
        self._update_interval = 10  # Update interval in seconds
        self._update_task = None

    async def connect(self, host):
        _LOGGER.debug("Connecting to %s", host)
        self.connection = create_connection(f"ws://{host}")

        self._update_task = asyncio.create_task(self._periodic_update())

    async def get_data(self):
        if self._data is None:
            # Fetch initial data if not available
            await self._update_data()
        return self._data

    async def _update_data(self):
        response = self.connection.recv()
        self._data = json.loads(response)

    async def _periodic_update(self):
        while True:
            await self._update_data()
            await asyncio.sleep(self._update_interval)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ecostream from a config entry."""

    host = entry.data[CONF_HOST]
    errors: dict[str, str] = {}

    api = MyApi()

    try:
        await api.connect(host)
        _LOGGER.info("Connected to %s", host)
    except Exception as e:
        _LOGGER.error("Cannot connect")
        errors["base"] = "unknown"
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
