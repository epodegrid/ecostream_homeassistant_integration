"""Sensor platform for the ecostream integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from datetime import timedelta  # Import timedelta

from homeassistant.helpers.entity import Entity # type: ignore
from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator # type: ignore
from homeassistant.const import UnitOfTime # type: ignore
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
    UnitOfTime,
)


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
        EcostreamFanEHASpeed(coordinator, entry),
        EcostreamFanSUPSpeed(coordinator, entry),
        EcostreamEco2EtaSensor(coordinator, entry),
        EcostreamRhEtaSensor(coordinator, entry),
        EcostreamTempEhaSensor(coordinator, entry),
        EcostreamTempEtaSensor(coordinator, entry),
        EcostreamTempOdaSensor(coordinator, entry),
        EcostreamTvocEtaSensor(coordinator, entry),
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
            update_interval=timedelta(seconds=30)  # Refresh interval in seconds
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
        return "Ecostream Frost Protection"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("frost_protection")

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
        return "Ecostream Qset"

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
        return "Ecostream Mode Time Left"

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

class EcostreamFanEHASpeed(EcostreamSensorBase): 

    @property
    def unique_id(self):
        return f"{self._entry_id}_fan_eha_speed"

    @property
    def name(self):
        return "Ecostream Fan Exhaust Speed"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("fan_eha_speed")

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:fan"

    @property
    def unit_of_measurement(self):
        return REVOLUTIONS_PER_MINUTE
    
class EcostreamFanSUPSpeed(EcostreamSensorBase):

    @property
    def unique_id(self):
        return f"{self._entry_id}_fan_sup_speed"

    @property
    def name(self):
        return "Ecostream Fan Supply Speed"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("fan_sup_speed")

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:fan"

    @property
    def unit_of_measurement(self):
        return REVOLUTIONS_PER_MINUTE

class EcostreamEco2EtaSensor(EcostreamSensorBase):
    """Sensor for eCO2 Return."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_eco2_eta"

    @property
    def name(self):
        return "Ecostream eCO2 Return"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("sensor_eco2_eta")

    @property
    def unit_of_measurement(self):
        return CONCENTRATION_PARTS_PER_MILLION

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:molecule-co2"

class EcostreamTempEhaSensor(EcostreamSensorBase):
    """Sensor for Exhaust Air Temperature."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_temp_eha"

    @property
    def name(self):
        return "Ecostream Exhaust Air Temperature"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("sensor_temp_eha")

    @property
    def unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:temperature-celsius"
    
class EcostreamTempEtaSensor(EcostreamSensorBase):
    """Sensor for Return Air Temperature."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_temp_eta"

    @property
    def name(self):
        return "Ecostream Return Air Temperature"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("sensor_temp_eta")

    @property
    def unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:temperature-celsius"

class EcostreamTempOdaSensor(EcostreamSensorBase):
    """Sensor for Outside Air Temperature."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_temp_oda"

    @property
    def name(self):
        return "Ecostream Outside Air Temperature"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("sensor_temp_oda")

    @property
    def unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:temperature-celsius"
    
class EcostreamTvocEtaSensor(EcostreamSensorBase):
    """Sensor for Total Volatile Organic Compounds Outside Air."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_tvoc_eta"

    @property
    def name(self):
        return "Ecostream Total Volatile Organic Compounds Outside Air"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("sensor_tvoc_eta")

    @property
    def unit_of_measurement(self):
        return CONCENTRATION_PARTS_PER_BILLION

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:air-purifier"
    
class EcostreamRhEtaSensor(EcostreamSensorBase):
    """Sensor for Relative Humidity Return."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_rh_eta"

    @property
    def name(self):
        return "Ecostream Relative Humidity Return"

    @property
    def state(self):
        return self.coordinator.data.get("status", {}).get("sensor_rh_eta")

    @property
    def unit_of_measurement(self):
        return "%"

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:molecule-co2"
