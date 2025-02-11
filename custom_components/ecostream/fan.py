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

SPEED_RANGE = (90, 350)

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
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    current_speed: float | None = None
    percentage: int | None = None

    def __init__(self, ws_client: EcostreamWebsocketsAPI, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the switch."""
        self._ws_client = ws_client
        self._hass = hass
        self._entry_id = entry.entry_id
    
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

    async def set_speed(self, speed: int):
        """Set the speed of the fan."""
        payload = {
            "config": {
                "man_override_set": speed,
                "man_override_set_time": 1800
            }
        }
        await self._ws_client.send_json(payload)
        self.current_speed = speed

        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        await self.set_speed(math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage)))

    async def async_turn_on(self, speed: Optional[str] = None, percentage: Optional[int] = None, **kwargs: Any) -> None:
        """Set the speed percentage of the fan to the provided percentage or """
        await self.set_speed(math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage or 100)))

    async def async_turn_off(self, **kwargs):
        """Turn the speed to the minimum value"""
        await self.set_speed(math.ceil(percentage_to_ranged_value(SPEED_RANGE, 0)))

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self.current_speed is None:
            return None
        return ranged_value_to_percentage(SPEED_RANGE, self.current_speed)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return int_states_in_range(SPEED_RANGE)
