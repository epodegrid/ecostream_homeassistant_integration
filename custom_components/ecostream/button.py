from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging
from typing import Any, cast

from .const import (
    CONF_PRESET_HIGH_PCT,
    CONF_PRESET_LOW_PCT,
    CONF_PRESET_MID_PCT,
    DEFAULT_PRESET_HIGH_PCT,
    DEFAULT_PRESET_LOW_PCT,
    DEFAULT_PRESET_MID_PCT,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    PRESET_HIGH,
    PRESET_LOW,
    PRESET_MID,
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

    async_add_entities([
        EcostreamPresetButton(coordinator, entry, PRESET_LOW),
        EcostreamPresetButton(coordinator, entry, PRESET_MID),
        EcostreamPresetButton(coordinator, entry, PRESET_HIGH),
    ])


class EcostreamPresetButton(
    CoordinatorEntity[EcostreamDataUpdateCoordinator], ButtonEntity
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
        preset: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._preset = preset
        self._attr_unique_id = f"{entry.entry_id}_preset_{preset}"
        self._attr_translation_key = f"preset_{preset}"
        self._attr_icon = "mdi:fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    def _preset_pct(self) -> int:
        opts = self._entry.options or {}
        if self._preset == PRESET_LOW:
            return int(opts.get(CONF_PRESET_LOW_PCT, DEFAULT_PRESET_LOW_PCT))
        if self._preset == PRESET_MID:
            return int(opts.get(CONF_PRESET_MID_PCT, DEFAULT_PRESET_MID_PCT))
        return int(opts.get(CONF_PRESET_HIGH_PCT, DEFAULT_PRESET_HIGH_PCT))

    async def async_press(self) -> None:
        if not self.coordinator.ws:
            _LOGGER.error("EcoStream WebSocket not connected, cannot set preset")
            return

        pct = self._preset_pct()

        config = cast(dict[str, Any], (self.coordinator.data or {}).get("config") or {})
        cap_min_raw = config.get("capacity_min")
        cap_max_raw = config.get("capacity_max")

        if cap_min_raw is None or cap_max_raw is None:
            _LOGGER.error("Invalid capacity range, cannot set preset")
            return

        try:
            cap_min = float(cap_min_raw)
            cap_max = float(cap_max_raw)
        except (TypeError, ValueError):
            _LOGGER.error("Invalid capacity range, cannot set preset")
            return

        if cap_max <= cap_min:
            _LOGGER.error("Invalid capacity range, cannot set preset")
            return

        qset = cap_min + (pct / 100.0) * (cap_max - cap_min)

        payload = {
            "config": {
                "man_override_set": float(qset),
                "man_override_set_time": 0,
            }
        }

        self.coordinator.mark_control_action()
        _LOGGER.debug("EcoStream preset %s → %s%% → Qset %.1f", self._preset, pct, qset)
        await self.coordinator.ws.send_json(payload)
