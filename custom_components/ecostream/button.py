from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging

from .const import (
    CONF_ALLOW_OVERRIDE_FILTER_DATE,
    CONF_FILTER_REPLACEMENT_DAYS,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
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

    async_add_entities(
        [
            EcostreamResetFilterButton(coordinator, entry),
        ]
    )


class EcostreamResetFilterButton(
    CoordinatorEntity[EcostreamDataUpdateCoordinator], ButtonEntity
):
    """Button to reset the filter replacement date."""

    _attr_has_entity_name = True
    _attr_name = "Reset Filter"
    _attr_icon = "mdi:air-filter"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reset_filter"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    async def async_press(self) -> None:
        """Reset the filter replacement date."""
        if not self.coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot reset filter"
            )
            return

        # Check if override is allowed
        opts = self._entry.options or {}
        allow_override = opts.get(
            CONF_ALLOW_OVERRIDE_FILTER_DATE, False
        )

        if not allow_override:
            _LOGGER.warning(
                "Filter date override is disabled. Enable 'Allow Override Filter Date' in integration options."
            )
            return

        import time

        filter_days = int(
            opts.get(
                CONF_FILTER_REPLACEMENT_DAYS,
                DEFAULT_FILTER_REPLACEMENT_DAYS,
            )
        )
        new_filter_datetime = int(time.time() + filter_days * 86400)

        payload = {"config": {"filter_datetime": new_filter_datetime}}

        _LOGGER.info(
            "EcoStream filter reset: new date in %s days (timestamp %s)",
            filter_days,
            new_filter_datetime,
        )
        await self.coordinator.ws.send_json(payload)
