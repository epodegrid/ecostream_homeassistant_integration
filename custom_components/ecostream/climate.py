from __future__ import annotations

import math
from typing import Any, Optional

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature, PRECISION_WHOLE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcostreamDataUpdateCoordinator
from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry[EcostreamDataUpdateCoordinator], 
    async_add_entities: AddEntitiesCallback,
):
    coordinator = entry.runtime_data

    climates = [
        EcostreamSummerComfortClimate(coordinator, entry),
    ]

    async_add_entities(climates, update_before_add=True)

class EcostreamSummerComfortClimate(CoordinatorEntity, ClimateEntity):
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_min_temp = 10
    _attr_max_temp = 30

    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_hvac_mode = self._current_hvac_mode()
        self._attr_hvac_action = self._current_hvac_action()
        self._attr_current_temperature = self._current_temperature()
        self._attr_target_temperature = self._target_temperature()

    @property
    def unique_id(self):
        return f"{self._entry_id}_summer_comfort_climate"

    @property
    def name(self):
        return "Ecostream Summer Comfort Climate"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api._host)},
            name="EcoStream",
            manufacturer="Buva",
            model="EcoStream",
        )
    
    async def async_set_temperature(self, temperature, **kwargs):
        payload = {
            "config": {
                "sum_com_temp": int(temperature)
            }
        }

        await self.coordinator.send_json(payload)
    
    async def async_set_hvac_mode(self, hvac_mode):
        enable_summer_control = hvac_mode == "cool"

        payload = {
            "config": {
                "sum_com_enabled": enable_summer_control,
            }
        }
        await self.coordinator.send_json(payload)
    
    def _current_hvac_mode(self) -> HVACMode:
        is_summer_control_enabled = self.coordinator.data["config"]["sum_com_enabled"]
        return HVACMode.COOL if is_summer_control_enabled else HVACMode.OFF
    
    def _current_hvac_action(self) -> HVACAction:
        bypass_position = self.coordinator.data["status"]["bypass_pos"]
        return HVACAction.COOLING if bypass_position > 0 else HVACAction.IDLE

    def _target_temperature(self) -> float:
        return self.coordinator.data["config"]["sum_com_temp"]

    def _current_temperature(self) -> float:
        return self.coordinator.data["status"]["sensor_temp_eta"]

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_hvac_mode = self._current_hvac_mode()
        self._attr_hvac_action = self._current_hvac_action()
        self._attr_current_temperature = self._current_temperature()
        self._attr_target_temperature = self._target_temperature()
        self.async_write_ha_state()
