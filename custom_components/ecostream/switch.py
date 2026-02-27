from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DEVICE_NAME,
    DEVICE_MODEL,
    BOOST_QSET,
    BOOST_OPTIONS,
    DEFAULT_BOOST_DURATION_MINUTES,
)

from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# Setup
# ============================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Register EcoStream switches and boost controls."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    entities: list = [
        EcostreamScheduleSwitch(coordinator, entry),
        EcostreamSummerComfortSwitch(coordinator, entry),
        EcostreamBoostSwitch(coordinator, entry),
        EcostreamBoostDurationSelect(coordinator, entry),
        EcostreamBoostRemainingSensor(coordinator, entry),
    ]

    async_add_entities(entities, update_before_add=True)


# ============================================================================
# Base Entity (shared device info)
# ============================================================================


class EcostreamBaseEntity(CoordinatorEntity):
    """Shared device info for EcoStream entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EcostreamDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    # Kleine helpers voor afgeleide klassen
    def _get_config(self) -> dict:
        return (self.coordinator.data or {}).get("config", {}) or {}

    def _get_status(self) -> dict:
        return (self.coordinator.data or {}).get("status", {}) or {}


# ============================================================================
# Schedule switch
# ============================================================================


class EcostreamScheduleSwitch(EcostreamBaseEntity, SwitchEntity):
    _attr_name = "Schedule Enabled"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_schedule_enabled"

    @property
    def is_on(self) -> bool:
        return bool(self._get_config().get("schedule_enabled", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._apply({"schedule_enabled": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._apply({"schedule_enabled": False})

    async def _apply(self, cfg: dict[str, Any]) -> None:
        if not self.coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot send schedule command"
            )
            return

        payload = {"config": cfg}
        self.coordinator.mark_control_action()
        await self.coordinator.ws.send_json(payload)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


# ============================================================================
# Summer Comfort switch
# ============================================================================


class EcostreamSummerComfortSwitch(EcostreamBaseEntity, SwitchEntity):
    _attr_name = "Summer Comfort"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_summer_comfort"

    @property
    def is_on(self) -> bool:
        return bool(self._get_config().get("sum_com_enabled", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._apply({"sum_com_enabled": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._apply({"sum_com_enabled": False})

    async def _apply(self, cfg: dict[str, Any]) -> None:
        if not self.coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot send summer comfort command"
            )
            return

        payload = {"config": cfg}
        self.coordinator.mark_control_action()
        await self.coordinator.ws.send_json(payload)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


# ============================================================================
# Boost Duration Select
# ============================================================================


class EcostreamBoostDurationSelect(EcostreamBaseEntity, SelectEntity):
    _attr_name = "Boost Duration"
    _attr_options = BOOST_OPTIONS

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_boost_duration"

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


# ============================================================================
# Boost Remaining Sensor (uit status.override_set_time_left)
# ============================================================================


class EcostreamBoostRemainingSensor(EcostreamBaseEntity, SensorEntity):
    _attr_name = "Boost Time Remaining"
    _attr_native_unit_of_measurement = "s"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_boost_time_left"

    @property
    def native_value(self) -> int:
        status = self._get_status()
        val = status.get("override_set_time_left")

        try:
            return int(val) if val is not None else 0
        except (TypeError, ValueError):
            return 0

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


# ============================================================================
# Boost switch
# ============================================================================


class EcostreamBoostSwitch(EcostreamBaseEntity, SwitchEntity):
    """Boost: tijdelijk hoge Qset met timer op de unit zelf."""

    _attr_name = "Boost"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_boost"

    @property
    def is_on(self) -> bool:
        """Boost is 'aan' zolang override_set_time_left > 0 is."""
        status = self._get_status()
        val = status.get("override_set_time_left")
        try:
            return int(val) > 0
        except (TypeError, ValueError):
            return False

    # ------------------------------
    # Boost AAN
    # ------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start (of reset) Boost: hoge Qset gedurende X minuten."""

        if not self.coordinator.ws:
            _LOGGER.error("EcoStream WebSocket not connected, cannot start boost")
            return

        config = self._get_config()

        # Preferentie: setpoint_high, anders capacity_max, anders fallback
        qset_raw = (
            config.get("setpoint_high")
            or config.get("capacity_max")
            or BOOST_QSET
        )

        try:
            qset = float(qset_raw)
        except (TypeError, ValueError):
            qset = float(BOOST_QSET)

        # ----------------------------
        # DUUR: altijd minstens 1 min
        # ----------------------------
        minutes = getattr(
            self.coordinator,
            "boost_duration_minutes",
            DEFAULT_BOOST_DURATION_MINUTES,
        )
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = DEFAULT_BOOST_DURATION_MINUTES

        if minutes < 1:
            _LOGGER.debug(
                "Boost duration %s is < 1 minute → using default %s",
                minutes,
                DEFAULT_BOOST_DURATION_MINUTES,
            )
            minutes = DEFAULT_BOOST_DURATION_MINUTES

        duration = minutes * 60  # seconden

        payload = {
            "config": {
                "man_override_set": qset,
                "man_override_set_time": duration,
            }
        }

        self.coordinator.mark_control_action()

        _LOGGER.debug(
            "Boost → ON (qset=%.1f, duration=%ss)",
            qset,
            duration,
        )

        await self.coordinator.ws.send_json(payload)

    # ------------------------------
    # Boost UIT (handmatig)
    # ------------------------------

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Handmatig Boost stoppen vóór het einde van de timer.

        We resetten alleen de override-timer op de unit:
        - man_override_set_time = 0

        De EcoStream valt dan terug op de normale regeling
        (setpoints / schema). Dat gedraagt zich zoals de officiële app.
        """
        if not self.coordinator.ws:
            _LOGGER.error("EcoStream WebSocket not connected, cannot stop boost")
            return

        payload = {
            "config": {
                "man_override_set_time": 0,
            }
        }

        self.coordinator.mark_control_action()

        _LOGGER.debug("Boost → OFF (clear man_override_set_time)")

        await self.coordinator.ws.send_json(payload)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update UI wanneer nieuwe EcoStream data binnenkomt."""
        self.async_write_ha_state()
