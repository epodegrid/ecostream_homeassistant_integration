from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import time
from typing import cast

from .const import DEVICE_MODEL, DEVICE_NAME, DOMAIN
from .coordinator import EcostreamDataUpdateCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EcoStream binary sensors."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        [
            EcostreamFilterReplacementWarningBinarySensor(
                coordinator, entry
            )
        ],
        update_before_add=True,
    )


class EcostreamFilterReplacementWarningBinarySensor(
    CoordinatorEntity[EcostreamDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Filter replacement due warning exposed as binary sensor."""

    _attr_has_entity_name = True
    _attr_name = "Filter Replacement Warning"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = (
            f"{entry.entry_id}_filter_replacement_warning_binary"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )
        self._refresh_state()

    def _refresh_state(self) -> None:
        data = cast(dict[str, object], self.coordinator.data or {})
        config = cast(dict[str, object], data.get("config") or {})
        ts = config.get("filter_datetime")

        if not isinstance(ts, (int, float)) or ts <= 0:
            self._attr_is_on = False
        else:
            self._attr_is_on = time.time() >= float(ts)

    @property
    def available(self) -> bool:  # type: ignore[override]
        data = cast(dict[str, object], self.coordinator.data or {})
        status = cast(dict[str, object], data.get("status") or {})
        return bool(status.get("connect_status", 1) == 1)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh_state()
        self.async_write_ha_state()
