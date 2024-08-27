"""Sensor platform for the ecostream integration."""
from __future__ import annotations

import logging

from homeassistant.helpers.entity import Entity # type: ignore
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator # type: ignore
from homeassistant.const import UnitOfTime # type: ignore

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up ecostream sensors from a config entry."""
    api = hass.data[DOMAIN][entry.entry_id]

    coordinator = EcostreamDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        EcostreamFrostProtectionSensor(coordinator, entry),
        EcostreamQsetSensor(coordinator, entry),
        EcostreamModeTimeLeftSensor(coordinator, entry),
    ]

    async_add_entities(sensors, update_before_add=True)

class EcostreamDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api):
        """Initialize."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=10,  # Refresh interval in seconds
        )

    async def _async_update_data(self):
        """Fetch data from the API."""
        return await self.api.get_data()

class EcostreamSensorBase(CoordinatorEntity, Entity):
    """Base class for ecostream sensors."""

    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry.entry_id

    @property
    def should_poll(self):
        """No polling needed, coordinator will handle updates."""
        return False

class EcostreamFrostProtectionSensor(EcostreamSensorBase):
    """Sensor for frost protection status."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_frost_protection"

    @property
    def name(self):
        return "Frost Protection"

    @property
    def is_on(self):
        return self.coordinator.data.get("status", {}).get("frost_protection", False)

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:snowflake-melt"

class EcostreamQsetSensor(EcostreamSensorBase):
    """Sensor for Qset status."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_qset"

    @property
    def name(self):
        return "Qset"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("qset")

class EcostreamModeTimeLeftSensor(EcostreamSensorBase):
    """Sensor for mode time left."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_mode_time_left"

    @property
    def name(self):
        return "Mode Time Left"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("override_set_time_left")

    @property
    def unit_of_measurement(self):
        return UnitOfTime.SECONDS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:timer-play"
