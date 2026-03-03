from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging
from typing import Any, cast

from .const import DEVICE_MODEL, DEVICE_NAME, DOMAIN
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the EcoStream fan platform."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data  # type: ignore[name-defined]

    async_add_entities(
        [EcostreamVentilationFan(coordinator, entry)],
        update_before_add=True,
    )


class EcostreamVentilationFan(CoordinatorEntity, FanEntity):
    """EcoStream main ventilation fan."""

    _attr_has_entity_name = True
    _attr_name = "Ventilation"
    _attr_should_poll = False
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
    )

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,  # type: ignore[name-defined]
        entry: ConfigEntry,
    ) -> None:
        """Initialize the EcoStream ventilation fan entity."""
        super().__init__(coordinator)
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_ventilation"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_percentage()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Supported features
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _status(self) -> dict:
        return (self.coordinator.data or {}).get("status", {}) or {}

    def _config(self) -> dict:
        return (self.coordinator.data or {}).get("config", {}) or {}

    def _get_qset(self) -> float:
        try:
            return float(self._status().get("qset", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _get_capacity_min(self) -> float | None:
        try:
            value = self._config().get("capacity_min")
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_capacity_max(self) -> float | None:
        try:
            value = self._config().get("capacity_max")
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # State → Home Assistant
    # ------------------------------------------------------------------
    @property
    def is_on(self) -> bool:
        return self._get_qset() > 0

    def _update_percentage(self) -> None:
        """Update the percentage attribute based on qset."""
        qset = self._get_qset()
        cap_min = self._get_capacity_min()
        cap_max = self._get_capacity_max()

        if cap_min is None or cap_max is None or cap_max <= cap_min:
            self._attr_percentage = None
        else:
            pct = round((qset - cap_min) / (cap_max - cap_min) * 100)
            self._attr_percentage = max(0, min(100, pct))

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        turn_on: bool = True,
        **kwargs: Any,
    ) -> None:
        pct = percentage or self._attr_percentage or 30
        await self.async_set_percentage(pct)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_percentage(0)

    async def async_set_percentage(self, percentage: int) -> None:
        percentage = max(0, min(100, int(percentage)))

        cap_min = self._get_capacity_min()
        cap_max = self._get_capacity_max()

        if cap_min is None or cap_max is None or cap_max <= cap_min:
            _LOGGER.error(
                "Invalid EcoStream capacity range (min=%s, max=%s). Cannot set fan.",
                cap_min,
                cap_max,
            )
            return

        qset = cap_min + (percentage / 100.0) * (cap_max - cap_min)
        coordinator = cast(Any, self.coordinator)

        if not coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected → cannot set fan"
            )
            return

        payload = {
            "config": {
                "man_override_set": float(qset),
                "man_override_set_time": 0,  # indefinite manual override
            }
        }

        coordinator.mark_control_action()
        _LOGGER.debug(
            "EcoStream ventilation: %s%% → Qset %.1f (min=%.1f max=%.1f)",
            percentage,
            qset,
            cap_min,
            cap_max,
        )

        await coordinator.ws.send_json(payload)
        self.async_write_ha_state()
