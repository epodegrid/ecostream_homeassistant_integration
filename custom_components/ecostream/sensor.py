"""Sensor platform for the ecostream integration."""
from __future__ import annotations

from homeassistant.helpers.entity import Entity # type: ignore
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity # type: ignore
from homeassistant.const import UnitOfTime # type: ignore
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)

from . import EcostreamDataUpdateCoordinator
from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry[EcostreamDataUpdateCoordinator], 
    async_add_entities: AddEntitiesCallback,
):
    """Set up ecostream sensors from a config entry."""
    coordinator = entry.runtime_data

    sensors = [
        EcostreamFilterReplacementWarningSensor(coordinator, entry),
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

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api._host)},
            name="EcoStream",
            manufacturer="Buva",
            model="EcoStream",
        )

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

class EcostreamFilterReplacementWarningSensor(EcostreamSensorBase):
    """Sensor for the filter replacement warning."""

    @property
    def unique_id(self):
        return f"{self._entry_id}_filter_replacement_warning"

    @property
    def name(self):
        return "Ecostream Filter Replacement"

    @property
    def state(self):
        errors = self.coordinator.data.get("status", {}).get("errors", [])

        return any(error["type"] == "ERROR_FILTER" for error in errors)

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:air-filter"

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
    
    @property
    def unit_of_measurement(self):
        return UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR

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
