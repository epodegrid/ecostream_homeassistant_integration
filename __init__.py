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
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


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

    async def set_man_override(self, value: float):
        _LOGGER.error("Broken pipe")
        data = {"config": {"man_override_set": value, "man_override_set_time": 900}}
        await self.connection.send(json.dumps(data))


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
    hass.data[DOMAIN]["api"] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def set_man_override_service(call):
        """Handle the service call."""
        value = call.data.get("value")
        api_instance = hass.data[DOMAIN].get("api")
        if api_instance:
            await api_instance.set_man_override(value)
            _LOGGER.info("Walalalala")
        else:
            _LOGGER.error("API instance is not available")

    try:
        hass.services.async_register(
            DOMAIN, "set_man_override", set_man_override_service
        )
        _LOGGER.info("Service 'set_man_override' registered successfully")
    except Exception as e:
        _LOGGER.error("Failed to register service 'set_man_override': %s", str(e))
        errors["base"] = "service_registration_failed"
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
