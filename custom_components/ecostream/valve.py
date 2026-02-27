from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.valve import (
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEVICE_NAME, DEVICE_MODEL
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data
    entities = [
        EcostreamBypassValve(coordinator, entry),
    ]
    async_add_entities(entities, update_before_add=True)


class EcostreamBypassValve(CoordinatorEntity, ValveEntity):
    """EcoStream Bypass Valve (0–100%)."""

    _attr_has_entity_name = True
    _attr_name = "Bypass Valve"
    _attr_supported_features = (
        ValveEntityFeature.OPEN |
        ValveEntityFeature.CLOSE |
        ValveEntityFeature.SET_POSITION
    )

    #
    # Required since HA 2024+: May NOT be None
    #
    _attr_reports_position = True  # FIX FOR YOUR EXCEPTION

    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_bypass_valve"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

        # Track local state
        self._position: Optional[int] = None

        # These may remain False unless you want animations
        self._is_opening = False
        self._is_closing = False

    #
    # Mandatory properties for ValveEntity
    #

    @property
    def reports_position(self) -> bool:
        """HA requires a fixed boolean — not optional."""
        return True

    @property
    def current_valve_position(self) -> Optional[int]:
        """Return 0–100%."""
        return self._position

    @property
    def is_open(self) -> Optional[bool]:
        """Open if > 0%."""
        if self._position is None:
            return None
        return self._position > 0

    @property
    def is_closed(self) -> Optional[bool]:
        if self._position is None:
            return None
        return self._position == 0

    @property
    def is_opening(self) -> bool:
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        return self._is_closing

    #
    # Incoming updates from coordinator (WS push)
    #
    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}
        status = data.get("status", {})

        new_pos = status.get("bypass_pos")
        if new_pos is not None:
            try:
                self._position = int(round(float(new_pos)))
            except Exception:
                pass

        self.async_write_ha_state()

    #
    # Commands to the EcoStream unit
    #

    async def async_open_valve(self, **kwargs: Any) -> None:
        await self.async_set_valve_position(100)

    async def async_close_valve(self, **kwargs: Any) -> None:
        await self.async_set_valve_position(0)

    async def async_set_valve_position(self, position: int) -> None:
        """Send bypass override command."""
        pos = max(0, min(100, int(position)))

        if not self.coordinator.ws:
            _LOGGER.error("Bypass valve: WS not connected")
            return

        self.coordinator.mark_control_action()

        payload = {"config": {"man_override_bypass": pos}}

        _LOGGER.debug("EcoStream → Set bypass to %s%%", pos)

        await self.coordinator.ws.send_json(payload)

        # Reflect temporary state while awaiting next WS push
        self._position = pos
        self.async_write_ha_state()
