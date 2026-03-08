from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging
from typing import Any

from .const import (
    CONF_SUMMER_COMFORT_TEMP,
    DEFAULT_BOOST_DURATION_MINUTES,
    DEFAULT_SUMMER_COMFORT_TEMP,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
)
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


# ============================================================================
# Setup
# ============================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register EcoStream switches and boost controls."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    entities: list[Any] = [
        EcostreamScheduleSwitch(coordinator, entry),
        EcostreamSummerComfortSwitch(coordinator, entry),
        EcostreamBoostSwitch(coordinator, entry),
    ]

    async_add_entities(entities, update_before_add=True)


# ============================================================================
# Base Entity (shared device info)
# ============================================================================


class EcostreamBaseEntity(
    CoordinatorEntity[EcostreamDataUpdateCoordinator]
):
    """Shared device info for EcoStream entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the EcoStream base entity with coordinator and config entry."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    # Kleine helpers voor afgeleide klassen
    def _get_config(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("config", {}) or {}

    def _get_status(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("status", {}) or {}


# ============================================================================
# Schedule switch
# ============================================================================


class EcostreamScheduleSwitch(EcostreamBaseEntity, SwitchEntity):
    _attr_translation_key = "schedule_enabled"
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_is_on = bool(
            self._get_config().get("schedule_enabled", False)
        )

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_schedule_enabled"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = bool(
            self._get_config().get("schedule_enabled", False)
        )
        self.async_write_ha_state()

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


# ============================================================================
# Summer Comfort switch
# ============================================================================


class EcostreamSummerComfortSwitch(EcostreamBaseEntity, SwitchEntity):
    _attr_translation_key = "summer_comfort"
    _attr_icon = "mdi:weather-sunny"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_is_on = bool(
            self._get_config().get("sum_com_enabled", False)
        )

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_summer_comfort"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = bool(
            self._get_config().get("sum_com_enabled", False)
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        opts = getattr(self._entry, "options", {}) or {}
        raw_temp = opts.get(
            CONF_SUMMER_COMFORT_TEMP, DEFAULT_SUMMER_COMFORT_TEMP
        )
        try:
            target_temp = int(raw_temp)
        except TypeError, ValueError:
            _LOGGER.error(
                "Invalid summer comfort temp %r, using default %s",
                raw_temp,
                DEFAULT_SUMMER_COMFORT_TEMP,
            )
            target_temp = DEFAULT_SUMMER_COMFORT_TEMP

        if target_temp < 15 or target_temp > 30:
            _LOGGER.error(
                "Summer comfort temp %s out of range (15-30); using default %s",
                target_temp,
                DEFAULT_SUMMER_COMFORT_TEMP,
            )
            target_temp = DEFAULT_SUMMER_COMFORT_TEMP

        await self._apply(
            {"sum_com_enabled": True, "sum_com_temp": target_temp}
        )

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


# ============================================================================
# Boost switch
# ============================================================================


class EcostreamBoostSwitch(EcostreamBaseEntity, SwitchEntity):
    """Boost: tijdelijk hoge Qset met timer (default: 15 minuten)."""

    _attr_translation_key = "boost"
    _attr_icon = "mdi:weather-windy"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        status = self._get_status()
        val = status.get("override_set_time_left")
        try:
            self._attr_is_on = val is not None and int(float(val)) > 0
        except TypeError, ValueError:
            self._attr_is_on = False

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_boost"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update UI wanneer nieuwe EcoStream data binnenkomt."""
        status = self._get_status()
        val = status.get("override_set_time_left")
        try:
            self._attr_is_on = val is not None and int(float(val)) > 0
        except TypeError, ValueError:
            self._attr_is_on = False
        self.async_write_ha_state()

    # ------------------------------
    # Boost AAN
    # ------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start (of reset) Boost: hoge Qset gedurende X minuten."""

        if not self.coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot start boost"
            )
            return

        config = self._get_config()

        qset_raw = config.get("setpoint_high")

        if qset_raw is None:
            _LOGGER.error(
                "Cannot start boost: config.setpoint_high is unavailable"
            )
            return

        try:
            qset = float(qset_raw)
        except TypeError, ValueError:
            _LOGGER.error(
                "Cannot start boost: invalid config.setpoint_high value %r",
                qset_raw,
            )
            return

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
        except TypeError, ValueError:
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
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot stop boost"
            )
            return

        payload = {
            "config": {
                "man_override_set_time": 0,
            }
        }

        self.coordinator.mark_control_action()

        _LOGGER.debug("Boost → OFF (clear man_override_set_time)")

        await self.coordinator.ws.send_json(payload)
