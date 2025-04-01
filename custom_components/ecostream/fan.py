from __future__ import annotations

import math
from typing import Any, Optional

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
    int_states_in_range,
)

from . import EcostreamDataUpdateCoordinator, EcostreamWebsocketsAPI
from .const import DOMAIN

PRESET_MODE_LOW = "low"
PRESET_MODE_MID = "mid"
PRESET_MODE_HIGH = "high"

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry[EcostreamDataUpdateCoordinator], 
    async_add_entities: AddEntitiesCallback,
):
    """Set up the fan entity."""
    coordinator = entry.runtime_data

    async_add_entities([EcoStreamFan(coordinator, entry)], update_before_add=True)


class EcoStreamFan(CoordinatorEntity, FanEntity):
    """Ecostream fan component."""

    _attr_supported_features = (
        FanEntityFeature.PRESET_MODE
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    _attr_preset_modes = [
        PRESET_MODE_LOW,
        PRESET_MODE_MID,
        PRESET_MODE_HIGH,
    ]
    
    current_speed: float | None = None

    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry.entry_id

        self.current_speed = self.coordinator.data.get("status", {}).get("qset")

        self._speed_range = (
            self.coordinator.api._data["config"]["capacity_min"], 
            self.coordinator.api._data["config"]["capacity_max"],
        )

        self._preset_speeds = {
            PRESET_MODE_LOW: self.coordinator.api._data["config"]["setpoint_low"],
            PRESET_MODE_MID: self.coordinator.api._data["config"]["setpoint_mid"],
            PRESET_MODE_HIGH: self.coordinator.api._data["config"]["setpoint_high"],
        }
    
    @property
    def unique_id(self):
        return f"{self._entry_id}_fan_control"

    @property
    def name(self):
        """Return the name of the fan."""
        return "Ecostream Fan"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api._host)},
            name="EcoStream",
            manufacturer="Buva",
            model="EcoStream",
        )

    async def set_speed(self, speed: int, preset_mode: Optional[str] = None):
        """Set the speed of the fan."""
        payload = {
            "config": {
                "man_override_set": speed,
                "man_override_set_time": 1800
            }
        }
        await self.coordinator.api.send_json(payload)
        self.current_speed = speed
        self.preset_mode = preset_mode

        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        await self.set_speed(math.ceil(percentage_to_ranged_value(self._speed_range, percentage)))

    async def async_turn_on(self, speed: Optional[str] = None, percentage: Optional[int] = None, **kwargs: Any) -> None:
        """Set the speed percentage of the fan to the provided percentage or """
        await self.set_speed(math.ceil(percentage_to_ranged_value(self._speed_range, percentage or 100)))

    async def async_turn_off(self, **kwargs):
        """Turn the speed to the minimum value"""
        await self.set_speed(math.ceil(percentage_to_ranged_value(self._speed_range, 0)))

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self.current_speed is None:
            return None
        return ranged_value_to_percentage(self._speed_range, self.current_speed)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return int_states_in_range(self._speed_range)
    
    async def async_set_preset_mode(self, preset_mode: str):
        """Set the preset mode of the fan."""
        speed = self._preset_speeds.get(preset_mode)

        if speed is None:
            raise Exception("Unknown preset mode")

        await self.set_speed(speed, preset_mode)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        new_speed = self.coordinator.data.get("status", {}).get("qset")

        if new_speed is None:
            return

        if new_speed != self.current_speed:
            self.preset_mode = None

        self.current_speed = new_speed

        self.async_write_ha_state()