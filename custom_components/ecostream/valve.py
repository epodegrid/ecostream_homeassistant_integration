from __future__ import annotations

import math
from typing import Any, Optional

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
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

    valves = [
        EcostreamBypassValve(coordinator, entry),
    ]

    async_add_entities(valves, update_before_add=True)

class EcostreamBypassValve(CoordinatorEntity, ValveEntity):
    reports_position = True

    _attr_supported_features = (
        ValveEntityFeature.CLOSE 
        | ValveEntityFeature.OPEN 
        | ValveEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry_id = entry.entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_bypass_valve"

    @property
    def name(self):
        return "Ecostream Bypass Valve"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api._host)},
            name="EcoStream",
            manufacturer="Buva",
            model="EcoStream",
        )
    
    async def async_set_valve_position(self, position: int):
        man_override_bypass_time = 24 * 3600

        if position == 0:
            # When the valve is closed, also disable the override to ensure
            #  other processes like summer comfort control can control the
            #  bypass valve again.
            man_override_bypass_time = 0

        payload = {
            "config": {
                "man_override_bypass": position,
                "man_override_bypass_time": man_override_bypass_time,  
            }
        }

        await self.coordinator.send_json(payload)

    @callback
    def _handle_coordinator_update(self):
        self._attr_current_valve_position = self.coordinator.data["status"]["bypass_pos"]
        
        config = self.coordinator.data["config"]

        # Most of the time, there is no movement in the bypass valve. Not are we able to determine
        #  the current action when the bypass is not currently in override mode.
        self._attr_is_closing = False
        self._attr_is_opening = False

        if config["man_override_bypass_time"] > 0:
            target = config["man_override_bypass"]

            if abs(self._attr_current_valve_position - target) < 0.1:
                # The difference is more likely due to rounding issues. Don't report a current action.
                pass
            elif self._attr_current_valve_position > target:
                self._attr_is_closing = True
            elif self._attr_current_valve_position < target:
                self._attr_is_opening = True
        elif not config["sum_com_enabled"] and self._attr_current_valve_position > 0:
            # If summer comfort is not enabled and the bypass is currently open, it will be closing
            self._attr_is_closing = True

        self.async_write_ha_state()
