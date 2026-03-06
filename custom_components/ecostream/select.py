from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging

from .const import (
    BOOST_OPTIONS,
    DEFAULT_BOOST_DURATION_MINUTES,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
)
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data
    async_add_entities([EcostreamBoostDurationSelect(coordinator, entry)], update_before_add=True)


class EcostreamBoostDurationSelect(
    CoordinatorEntity[EcostreamDataUpdateCoordinator], SelectEntity
):
    _attr_has_entity_name = True
    _attr_translation_key = "boost_duration"
    _attr_options = BOOST_OPTIONS
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_boost_duration"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    @property
    def current_option(self) -> str | None:
        minutes = getattr(
            self.coordinator,
            "boost_duration_minutes",
            DEFAULT_BOOST_DURATION_MINUTES,
        )
        return str(minutes)

    async def async_select_option(self, option: str) -> None:
        try:
            minutes = int(option)
        except (TypeError, ValueError):
            _LOGGER.warning("Invalid boost duration option: %s", option)
            return

        self.coordinator.boost_duration_minutes = minutes  # type: ignore[attr-defined]
        self.async_write_ha_state()
