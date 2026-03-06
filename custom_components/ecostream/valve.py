from __future__ import annotations

from homeassistant.components.valve import (
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging
import time
from typing import Any

from .const import DEVICE_MODEL, DEVICE_NAME, DOMAIN
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data
    entities = [
        EcostreamBypassValve(coordinator, entry),
    ]
    async_add_entities(entities, update_before_add=True)


class EcostreamBypassValve(
    CoordinatorEntity[EcostreamDataUpdateCoordinator], ValveEntity
):
    """EcoStream Bypass Valve (0-100%)."""

    _attr_has_entity_name = True
    _attr_translation_key = "bypass_valve"
    _attr_icon = "mdi:valve"
    _attr_supported_features = (
        ValveEntityFeature.OPEN
        | ValveEntityFeature.CLOSE
        | ValveEntityFeature.SET_POSITION
    )

    _attr_reports_position = True

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the bypass valve entity with coordinator and config entry."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_bypass_valve"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

        self._position: int | None = None
        self._is_opening = False
        self._is_closing = False
        self._override_until: float = 0.0

    @property
    def reports_position(self) -> bool:
        return True

    @property
    def current_valve_position(self) -> int | None:
        return self._position

    @property
    def is_open(self) -> bool | None:
        if self._position is None:
            return None
        return self._position > 0

    @property
    def is_closed(self) -> bool | None:
        if self._position is None:
            return None
        return self._position == 0

    @property
    def is_opening(self) -> bool:
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        return self._is_closing

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}
        status = data.get("status", {})

        new_pos = status.get("bypass_pos")
        if new_pos is not None and time.time() >= self._override_until:
            try:
                self._position = max(0, min(100, round(float(new_pos))))
            except Exception:
                pass

        self.async_write_ha_state()

    async def async_open_valve(self, **kwargs: Any) -> None:
        await self.async_set_valve_position(100)

    async def async_close_valve(self, **kwargs: Any) -> None:
        await self.async_set_valve_position(0)

    async def async_set_valve_position(self, position: int) -> None:
        pos = max(0, min(100, int(position)))

        if not self.coordinator.ws:
            _LOGGER.error("Bypass valve: WS not connected")
            return

        self.coordinator.mark_control_action()

        payload = {"config": {"man_override_bypass": pos}}
        _LOGGER.debug("EcoStream → Set bypass to %s%%", pos)

        await self.coordinator.ws.send_json(payload)

        self._position = pos
        self._override_until = time.time() + 30.0
        self.async_write_ha_state()
