from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEVICE_NAME, DEVICE_MODEL
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Register EcoStream number entities."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    entities = [
        EcostreamQsetNumber(coordinator, entry),
    ]

    async_add_entities(entities, update_before_add=True)


class EcostreamQsetNumber(CoordinatorEntity, NumberEntity):
    """Writeable Qset control for ventilation capacity."""

    _attr_has_entity_name = True
    _attr_name = "Qset"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "m³/h"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_qset_number"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

        # Default min/max before data arrives
        self._attr_native_min_value = 60
        self._attr_native_max_value = 350
        self._attr_native_step = 1

    #
    # VALUE FROM DEVICE
    #
    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        status = data.get("status", {})
        qset = status.get("qset")

        try:
            return float(qset) if qset is not None else None
        except Exception:
            return None

    #
    # UPDATE MIN/MAX FROM DEVICE CONFIG
    #
    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}
        config = data.get("config") or {}

        cap_min = config.get("capacity_min")
        cap_max = config.get("capacity_max")

        if isinstance(cap_min, (int, float)):
            self._attr_native_min_value = float(cap_min)

        if isinstance(cap_max, (int, float)):
            self._attr_native_max_value = float(cap_max)

        self.async_write_ha_state()

    #
    # WRITE NEW VALUE TO DEVICE
    #
    async def async_set_native_value(self, value: float) -> None:
        """Send new Qset to EcoStream device."""

        if not self.coordinator.ws:
            _LOGGER.error("Cannot set Qset: WebSocket not connected")
            return

        # Ensure fast-push mode activates
        self.coordinator.mark_control_action()

        payload = {"config": {"man_override_set": float(value)}}

        _LOGGER.debug("EcoStream Qset → setting to %.1f", value)

        await self.coordinator.ws.send_json(payload)
