from __future__ import annotations
from dateutil.relativedelta import relativedelta
from homeassistant.util import dt

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity # type: ignore
from homeassistant.const import UnitOfTime # type: ignore

from . import EcostreamDataUpdateCoordinator, EcostreamWebsocketsAPI
from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[EcostreamDataUpdateCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator = entry.runtime_data
    
    buttons = [
        FilterResetButton(coordinator, entry)
    ]

    # Add your button entity
    async_add_entities(buttons)

class EcostreamButtonBase(CoordinatorEntity, ButtonEntity):
    """Base class for ecostream buttons."""
    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api._host)},
            name="EcoStream",
            manufacturer="Buva",
            model="EcoStream",
        )

class FilterResetButton(EcostreamButtonBase):
    """Button that resets the filter replacement date."""

    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the button"""
        super().__init__(coordinator, entry)
        self._last_pressed = None

    @property
    def unique_id(self):
        return f"{self._entry_id}_reset_filter"

    @property
    def name(self):
        return "Ecostream Reset Filter"

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:air-filter"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "last_pressed": self._last_pressed
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        
        # Get current date and time
        now = dt.utcnow()
        self._last_pressed = now

        # Add 3 months (which seems to correspond with what the ecostream app does)
        nextReplacementDate = now + relativedelta(months=3)
        nextReplacementTimestamp = int(nextReplacementDate.timestamp())

        # Send the new filter replacement date to the unit
        payload = {
            "config": {
                "filter_datetime": nextReplacementTimestamp
            }
        }
        await self.coordinator.send_json(payload)
