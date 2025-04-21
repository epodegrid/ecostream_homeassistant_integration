from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry 
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcostreamDataUpdateCoordinator, EcostreamWebsocketsAPI
from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[EcostreamDataUpdateCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    
    buttons = [
        ScheduleSwitch(coordinator, entry)
    ]

    async_add_entities(buttons)

class EcostreamSwitchBase(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api._host)},
            name="EcoStream",
            manufacturer="Buva",
            model="EcoStream",
        )

class ScheduleSwitch(EcostreamSwitchBase):
    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)

    @property
    def unique_id(self):
        return f"{self._entry_id}_schedule_switch"

    @property
    def name(self):
        return "Schedule"

    @property
    def icon(self):
        return "mdi:calendar-month-outline"
    
    @callback
    def _handle_coordinator_update(self):
        self._attr_is_on = self.coordinator.data["config"]["schedule_enabled"]
        self.async_write_ha_state()
    
    async def async_turn_on(self):
        await self._change_schedule(True)

    async def async_turn_off(self):
        await self._change_schedule(False)
    
    async def _change_schedule(self, schedule_enabled: bool):
        payload = {
            "config": {
                "schedule_enabled": schedule_enabled
            }
        }
        await self.coordinator.send_json(payload)