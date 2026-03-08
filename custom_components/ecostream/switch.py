from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import inspect
import logging
from typing import Any

from .const import (
    CONF_PRESET_OVERRIDE_MINUTES,
    CONF_SUMMER_COMFORT_TEMP,
    DEFAULT_BOOST_DURATION_MINUTES,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
    DEFAULT_SUMMER_COMFORT_TEMP,
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
        EcostreamBypassSwitch(coordinator, entry),
        EcostreamBoostSwitch(coordinator, entry),
        EcostreamPresetSwitch(coordinator, entry, PRESET_LOW),
        EcostreamPresetSwitch(coordinator, entry, PRESET_MID),
        EcostreamPresetSwitch(coordinator, entry, PRESET_HIGH),
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

    async def _apply_config(
        self, cfg: dict[str, Any], action: str
    ) -> None:
        sender = getattr(self.coordinator, "async_send_config", None)
        if sender is not None:
            result = sender(cfg, action)
            if inspect.isawaitable(result):
                await result
                return

        if not self.coordinator.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot send %s command",
                action,
            )
            return

        self.coordinator.mark_control_action()
        await self.coordinator.ws.send_json({"config": cfg})


class EcostreamConfigSwitch(EcostreamBaseEntity, SwitchEntity):
    _config_key: str
    _log_action: str

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_is_on = bool(
            self._get_config().get(self._config_key, False)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = bool(
            self._get_config().get(self._config_key, False)
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._apply_config(
            {self._config_key: True}, self._log_action
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._apply_config(
            {self._config_key: False}, self._log_action
        )


# ============================================================================
# Schedule switch
# ============================================================================


class EcostreamScheduleSwitch(EcostreamConfigSwitch):
    _attr_translation_key = "schedule_enabled"
    _attr_icon = "mdi:calendar-clock"
    _config_key = "schedule_enabled"
    _log_action = "schedule"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_schedule_enabled"


# ============================================================================
# Summer Comfort switch
# ============================================================================


class EcostreamSummerComfortSwitch(EcostreamConfigSwitch):
    _attr_translation_key = "summer_comfort"
    _attr_icon = "mdi:weather-sunny"
    _config_key = "sum_com_enabled"
    _log_action = "summer comfort"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_summer_comfort"

    async def async_turn_on(self, **kwargs: Any) -> None:
        opts = getattr(self._entry, "options", {}) or {}
        raw_temp = opts.get(
            CONF_SUMMER_COMFORT_TEMP, DEFAULT_SUMMER_COMFORT_TEMP
        )
        try:
            target_temp = int(raw_temp)
        except (TypeError, ValueError):
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

        await self._apply_config(
            {"sum_com_enabled": True, "sum_com_temp": target_temp},
            self._log_action,
        )


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
        except (TypeError, ValueError):
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
        except (TypeError, ValueError):
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
        except (TypeError, ValueError):
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

        _LOGGER.debug(
            "Boost → ON (qset=%.1f, duration=%ss)",
            qset,
            duration,
        )

        await self._apply_config(payload["config"], "boost")

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

        _LOGGER.debug("Boost → OFF (clear man_override_set_time)")

        await self._apply_config(payload["config"], "boost")


# ============================================================================
# Bypass switch
# ============================================================================


class EcostreamBypassSwitch(EcostreamBaseEntity, SwitchEntity):
    _attr_translation_key = "bypass_valve"
    _attr_icon = "mdi:valve"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_is_on = self._is_bypass_open()

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_bypass_valve"

    def _is_bypass_open(self) -> bool:
        pos_raw = self._get_status().get("bypass_pos")
        if pos_raw is None:
            return False
        try:
            return float(pos_raw) > 0
        except (TypeError, ValueError):
            return False

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self._is_bypass_open()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._apply_config({"man_override_bypass": 100}, "bypass")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._apply_config({"man_override_bypass": 0}, "bypass")


# ==========================================================================
# Preset switches
# ==========================================================================


class EcostreamPresetSwitch(EcostreamBaseEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:fan"

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
        preset: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._preset = preset
        self._attr_translation_key = f"preset_{preset}"
        self._attr_unique_id = f"{entry.entry_id}_preset_{preset}"
        self._attr_is_on = self._is_active()

    def _get_setpoint(self) -> float | None:
        config = self._get_config()
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

    def _is_active(self) -> bool:
        qset_raw = self._get_status().get("qset")
        setpoint = self._get_setpoint()
        if qset_raw is None or setpoint is None:
            return False
        try:
            qset = float(qset_raw)
        except (TypeError, ValueError):
            return False
        return abs(qset - setpoint) <= 0.1

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self._is_active()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        qset = self._get_setpoint()
        if qset is None:
            _LOGGER.warning(
                "EcoStream setpoint for preset %s not available in config data",
                self._preset,
            )
            return

        opts = getattr(self._entry, "options", {}) or {}
        override_minutes = int(
            opts.get(
                CONF_PRESET_OVERRIDE_MINUTES,
                DEFAULT_PRESET_OVERRIDE_MINUTES,
            )
        )

        payload = {
            "man_override_set": qset,
            "man_override_set_time": override_minutes * 60,
        }

        _LOGGER.debug(
            "EcoStream preset %s → Qset %.1f", self._preset, qset
        )
        await self._apply_config(payload, f"preset {self._preset}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._apply_config(
            {"man_override_set_time": 0}, f"preset {self._preset}"
        )
