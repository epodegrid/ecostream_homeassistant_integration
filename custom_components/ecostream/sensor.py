from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging
from typing import Any, cast

from .const import (
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
)
from .coordinator import EcostreamDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_get(
    data: Mapping[str, Any], path: list[str], default: Any = None
) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cast(dict[str, Any], cur)[key]
    return cur


def _format_uptime(seconds: int) -> str:
    if seconds < 0:
        return "0m"

    days = seconds // 86400
    rem = seconds % 86400
    hours = rem // 3600
    rem %= 3600
    minutes = rem // 60

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Extended EntityDescription
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EcostreamSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Mapping[str, Any]], Any] | None = None
    is_date: bool = False


# ---------------------------------------------------------------------------
# Base + Predefined Sensor Descriptions
# ---------------------------------------------------------------------------

SENSOR_DESCRIPTIONS: tuple[EcostreamSensorDescription, ...] = (
    # -------------------------------------------------------------------
    # STATUS
    # -------------------------------------------------------------------
    EcostreamSensorDescription(
        key="bypass_position",
        name="Bypass Position",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _deep_get(d, ["status", "bypass_pos"]),
    ),
    EcostreamSensorDescription(
        key="eco2_return",
        name="eCO₂ Return",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement="ppm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "sensor_eco2_eta"]))
            is None
            else round(float(v))
        ),
    ),
    EcostreamSensorDescription(
        key="tvoc_return",
        name="TVOC Return",
        icon="mdi:chemical-weapon",
        native_unit_of_measurement="ppb",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "sensor_tvoc_eta"]))
            is None
            else round(float(v))
        ),
    ),
    EcostreamSensorDescription(
        key="humidity_return",
        name="Humidity Return",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "sensor_rh_eta"])) is None
            else round(float(v))
        ),
    ),
    EcostreamSensorDescription(
        key="temperature_eha",
        name="Temperature EHA",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "sensor_temp_eha"]))
            is None
            else round(float(v), 1)
        ),
    ),
    EcostreamSensorDescription(
        key="temperature_eta",
        name="Temperature ETA",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "sensor_temp_eta"]))
            is None
            else round(float(v), 1)
        ),
    ),
    EcostreamSensorDescription(
        key="temperature_oda",
        name="Temperature ODA",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "sensor_temp_oda"]))
            is None
            else round(float(v), 1)
        ),
    ),
    EcostreamSensorDescription(
        key="fan_exhaust_speed",
        name="Fan Exhaust Speed",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "fan_eha_speed"])) is None
            else round(float(v))
        ),
    ),
    EcostreamSensorDescription(
        key="fan_supply_speed",
        name="Fan Supply Speed",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "fan_sup_speed"])) is None
            else round(float(v))
        ),
    ),
    EcostreamSensorDescription(
        key="qset",
        name="Qset",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "qset"])) is None
            else round(float(v))
        ),
    ),
    EcostreamSensorDescription(
        key="mode_time_left",
        name="Mode Time Left",
        native_unit_of_measurement="s",
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["status", "override_set_time_left"]))
            is None
            else int(v)
        ),
    ),
    EcostreamSensorDescription(
        key="frost_protection_active",
        name="Frost Protection Active",
        value_fn=lambda d: bool(
            _deep_get(d, ["status", "frost_protection"], False)
        ),
    ),
    # -------------------------------------------------------------------
    # HEAT RECOVERY EFFICIENCY (NEW)
    # -------------------------------------------------------------------
    EcostreamSensorDescription(
        key="efficiency",
        name="Heat Recovery Efficiency",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _calc_efficiency(d),
    ),
    # -------------------------------------------------------------------
    # CONFIG
    # -------------------------------------------------------------------
    EcostreamSensorDescription(
        key="schedule_enabled",
        name="Schedule Enabled",
        value_fn=lambda d: bool(
            _deep_get(d, ["config", "schedule_enabled"], False)
        ),
    ),
    EcostreamSensorDescription(
        key="summer_comfort_enabled",
        name="Summer Comfort Enabled",
        value_fn=lambda d: bool(
            _deep_get(d, ["config", "sum_com_enabled"], False)
        ),
    ),
    EcostreamSensorDescription(
        key="summer_comfort_temp",
        name="Summer Comfort Temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["config", "sum_com_temp"])) is None
            else round(float(v), 1)
        ),
    ),
    EcostreamSensorDescription(
        key="filter_replacement_date",
        name="Filter Replacement Date",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_date=True,
        value_fn=lambda d: _deep_get(d, ["config", "filter_datetime"]),
    ),
    EcostreamSensorDescription(
        key="filter_replacement_warning",
        name="Filter Replacement Warning",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: bool(
            _deep_get(d, ["config", "filter_datetime"], 0)
        ),
    ),
    # -------------------------------------------------------------------
    # SYSTEM
    # -------------------------------------------------------------------
    EcostreamSensorDescription(
        key="uptime",
        name="Uptime",
        translation_key="uptime",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _deep_get(d, ["system", "uptime"]),
    ),
    # -------------------------------------------------------------------
    # WIFI
    # -------------------------------------------------------------------
    EcostreamSensorDescription(
        key="wifi_ip",
        name="WiFi IP",
        translation_key="wifi_ip",
        icon="mdi:wifi",
        value_fn=lambda d: _deep_get(d, ["comm_wifi", "wifi_ip"]),
    ),
    EcostreamSensorDescription(
        key="wifi_ssid",
        name="WiFi SSID",
        translation_key="wifi_ssid",
        icon="mdi:wifi",
        value_fn=lambda d: _deep_get(d, ["comm_wifi", "ssid"]),
    ),
    EcostreamSensorDescription(
        key="wifi_rssi",
        name="WiFi RSSI",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        translation_key="wifi_rssi",
        icon="mdi:wifi-strength-2",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (
            None
            if (v := _deep_get(d, ["comm_wifi", "rssi"])) is None
            else int(v)
        ),
    ),
)


# ---------------------------------------------------------------------------
# Efficiency calculation function
# ---------------------------------------------------------------------------


def _calc_efficiency(data: Mapping[str, Any]) -> float | None:
    """η = (ETA - EHA) / (ETA - ODA) x 100."""

    try:
        eta = float(_deep_get(data, ["status", "sensor_temp_eta"]))
        eha = float(_deep_get(data, ["status", "sensor_temp_eha"]))
        oda = float(_deep_get(data, ["status", "sensor_temp_oda"]))
    except Exception:
        return None

    denominator = eta - oda
    numerator = eta - eha

    if denominator <= 0:
        return None

    eff = (numerator / denominator) * 100.0

    if eff < 0:
        eff = 0.0
    if eff > 100:
        eff = 100.0

    return round(eff, 1)


# ---------------------------------------------------------------------------
# Sensor entity implementation
# ---------------------------------------------------------------------------


class EcostreamBaseSensor(
    CoordinatorEntity[EcostreamDataUpdateCoordinator], SensorEntity
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
        description: EcostreamSensorDescription,
    ) -> None:
        """Initialize the Ecostream sensor entity."""
        super().__init__(coordinator)

        self.entity_description = description
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )

    @property
    def available(self) -> bool:
        data = cast(dict[str, Any], self.coordinator.data or {})
        status = cast(dict[str, Any], data.get("status") or {})
        return bool(status.get("connect_status", 1) == 1)

    @property
    def native_value(self) -> Any:
        desc = self.entity_description
        data = self.coordinator.data or {}

        try:
            raw = (
                desc.value_fn(data)
                if isinstance(desc, EcostreamSensorDescription)
                and desc.value_fn
                else None
            )
        except Exception as err:
            _LOGGER.debug("Value error in %s: %s", desc.key, err)
            return None

        if raw is None:
            return None

        # Date parsing
        if (
            isinstance(desc, EcostreamSensorDescription)
            and desc.is_date
        ):
            try:
                if isinstance(raw, (int, float)):
                    return datetime.fromtimestamp(raw, tz=UTC).date()
                if isinstance(raw, datetime):
                    return raw.date()
                return raw
            except Exception:
                return None

        # Uptime formatting
        if desc.key == "uptime":
            try:
                return _format_uptime(int(raw))
            except Exception:
                return None

        return raw

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data

    entities = [
        EcostreamBaseSensor(coordinator, entry, desc)
        for desc in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities, update_before_add=True)
