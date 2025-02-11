from __future__ import annotations

import math
from typing import Any

from homeassistant.helpers.entity import DeviceInfo

from config.custom_components.ecostream import EcostreamWebsocketsAPI
from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
    int_states_in_range,
)

from . import EcostreamWebsocketsAPI
from .const import DOMAIN

PRESET_MODE_LOW = "low"
PRESET_MODE_MID = "mid"
PRESET_MODE_HIGH = "high"

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback,
):
    """Set up the fan entity."""
    ws_client: EcostreamWebsocketsAPI = hass.data[DOMAIN]["ws_client"]
    async_add_entities([EcoStreamFan(ws_client, hass, entry)], update_before_add=True)


class EcoStreamFan(FanEntity):
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

    _preset_mode: str | None = None
    current_speed: float | None = None

    def __init__(self, ws_client: EcostreamWebsocketsAPI, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the switch."""
        self._ws_client = ws_client
        self._hass = hass
        self._entry_id = entry.entry_id
        
        self._speed_range = (
            self._ws_client._config["capacity_min"], 
            self._ws_client._config["capacity_max"],
        )

        self._preset_speeds = {
            PRESET_MODE_LOW: self._ws_client._config["setpoint_low"],
            PRESET_MODE_MID: self._ws_client._config["setpoint_mid"],
            PRESET_MODE_HIGH: self._ws_client._config["setpoint_high"],
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
            identifiers={(DOMAIN, self._ws_client._host)},
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
        await self._ws_client.send_json(payload)
        self.current_speed = speed
        self._preset_mode = preset_mode

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

    @property
    def preset_mode(self) -> str:
        """Return the preset mode."""
        if self._preset_mode is None:
            return None

        return self._preset_mode
    
    async def async_set_preset_mode(self, preset_mode: str):
        """Set the preset mode of the fan."""
        speed = self._preset_speeds.get(preset_mode)

        if speed is None:
            raise Exception("Unknown preset mode")

        await self.set_speed(speed, preset_mode)
