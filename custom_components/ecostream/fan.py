from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging
from typing import Any

from .const import (
    CONF_PRESET_OVERRIDE_MINUTES,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    PRESET_HIGH,
    PRESET_LOW,
    PRESET_MID,
    PRESET_MODES,
)
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EcoStream fan platform."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    async_add_entities(
        [EcostreamVentilationFan(coordinator, entry)],
        update_before_add=True,
    )


class EcostreamVentilationFan(
    CoordinatorEntity[EcostreamDataUpdateCoordinator], FanEntity
):
    """EcoStream main ventilation fan."""

    _attr_has_entity_name = True
    _attr_translation_key = "ventilation"
    _attr_should_poll = False
    _attr_icon = "mdi:fan"
    coordinator: EcostreamDataUpdateCoordinator

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
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

        features = FanEntityFeature(0)
        for name in ("TURN_ON", "TURN_OFF", "PRESET_MODE"):
            val = getattr(FanEntityFeature, name, None)
            if val is not None:
                features |= val
        self._attr_supported_features = features
        self._attr_preset_modes = PRESET_MODES
        self._attr_preset_mode: str | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _status(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("status", {}) or {}

    def _config(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("config", {}) or {}

    def _get_qset(self) -> float:
        try:
            return float(self._status().get("qset", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _get_setpoint(self, preset: str) -> float | None:
        config = self._config()
        key = {
            PRESET_LOW: "setpoint_low",
            PRESET_MID: "setpoint_mid",
            PRESET_HIGH: "setpoint_high",
        }.get(preset)
        if key is None:
            return None
        try:
            value = config.get(key)
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _calculate_preset(self, qset: float) -> str | None:
        low = self._get_setpoint(PRESET_LOW)
        mid = self._get_setpoint(PRESET_MID)
        high = self._get_setpoint(PRESET_HIGH)
        if low is None or mid is None or high is None:
            return None
        if abs(qset - low) <= abs(qset - mid) and abs(
            qset - low
        ) <= abs(qset - high):
            return PRESET_LOW
        if abs(qset - mid) <= abs(qset - high):
            return PRESET_MID
        return PRESET_HIGH

    # ------------------------------------------------------------------
    # State → Home Assistant
    # ------------------------------------------------------------------
    @property
    def is_on(self) -> bool:
        return self._get_qset() > 0

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self.async_set_preset_mode(preset_mode or PRESET_MID)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_preset_mode(PRESET_LOW)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        qset = self._get_setpoint(preset_mode)
        if qset is None:
            _LOGGER.error(
                "EcoStream: no setpoint available for preset %s",
                preset_mode,
            )
            return

        if not self.coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected → cannot set preset"
            )
            return

        opts = self._entry.options or {}
        override_minutes = int(
            opts.get(
                CONF_PRESET_OVERRIDE_MINUTES,
                DEFAULT_PRESET_OVERRIDE_MINUTES,
            )
        )
        payload = {
            "config": {
                "man_override_set": qset,
                "man_override_set_time": override_minutes * 60,
            }
        }

        self._attr_preset_mode = preset_mode
        self.coordinator.mark_control_action()
        _LOGGER.debug(
            "EcoStream preset %s → Qset %.1f", preset_mode, qset
        )

        await self.coordinator.ws.send_json(payload)
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        qset = self._get_qset()
        self._attr_preset_mode = (
            self._calculate_preset(qset) if qset > 0 else None
        )
        self.async_write_ha_state()
