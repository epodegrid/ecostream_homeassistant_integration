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
    CONF_ALLOW_OVERRIDE_FILTER_DATE,
    CONF_FILTER_REPLACEMENT_DAYS,
    CONF_PRESET_OVERRIDE_MINUTES,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
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

    async_add_entities(
        [
            EcostreamPresetButton(coordinator, entry, PRESET_LOW),
            EcostreamPresetButton(coordinator, entry, PRESET_MID),
            EcostreamPresetButton(coordinator, entry, PRESET_HIGH),
            EcostreamResetFilterButton(coordinator, entry),
        ]
    )


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
        self._attr_name = preset
        self._attr_icon = "mdi:fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    def _get_setpoint(self) -> float | None:
        config = cast(
            dict[str, Any],
            (self.coordinator.data or {}).get("config") or {},
        )
        key = {
            PRESET_LOW: "setpoint_low",
            PRESET_MID: "setpoint_mid",
            PRESET_HIGH: "setpoint_high",
        }.get(self._preset)
        if key is None:
            return None
        try:
            value = config.get(key)
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # type: ignore[override]
        qset = self._get_setpoint()
        return {"setpoint": qset, "unit": "m³/h"}

    async def async_press(self) -> None:
        if not self.coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot set preset"
            )
            return

        qset = self._get_setpoint()

        if qset is None:
            _LOGGER.warning(
                "EcoStream setpoint for preset %s not available in config data",
                self._preset,
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

        self.coordinator.mark_control_action()
        _LOGGER.debug(
            "EcoStream preset %s → Qset %.1f", self._preset, qset
        )
        await self.coordinator.ws.send_json(payload)


class EcostreamResetFilterButton(
    CoordinatorEntity[EcostreamDataUpdateCoordinator], ButtonEntity
):
    """Button to reset the filter replacement date."""

    _attr_has_entity_name = True
    _attr_translation_key = "reset_filter"
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
