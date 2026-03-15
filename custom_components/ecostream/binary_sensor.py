from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import time
from typing import Any, cast

from .const import DEVICE_MODEL, DEVICE_NAME, DOMAIN
from .coordinator import EcostreamDataUpdateCoordinator

PARALLEL_UPDATES = 0


def _deep_get(
    data: Mapping[str, Any], path: list[str], default: Any = None
) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cast(dict[str, Any], cur)[key]
    return cur


def _bool_value(
    path: list[str], default: bool = False
) -> Callable[[Mapping[str, Any]], bool]:
    def _fn(data: Mapping[str, Any]) -> bool:
        return bool(_deep_get(data, path, default))

    return _fn


@dataclass(frozen=True)
class EcostreamBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[Mapping[str, Any]], bool] = lambda _: False


BINARY_SENSOR_DESCRIPTIONS: tuple[
    EcostreamBinarySensorDescription, ...
] = (
    EcostreamBinarySensorDescription(
        key="frost_protection_active",
        name="Frost Protection Active",
        value_fn=_bool_value(["status", "frost_protection"], False),
    ),
    EcostreamBinarySensorDescription(
        key="schedule_enabled",
        name="Schedule Enabled",
        value_fn=_bool_value(["config", "schedule_enabled"], False),
    ),
    EcostreamBinarySensorDescription(
        key="summer_comfort_enabled",
        name="Summer Comfort Enabled",
        value_fn=_bool_value(["config", "sum_com_enabled"], False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EcoStream binary sensors."""
    coordinator: EcostreamDataUpdateCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        EcostreamFilterReplacementWarningBinarySensor(
            coordinator, entry
        ),
        *[
            EcostreamBaseBinarySensor(coordinator, entry, desc)
            for desc in BINARY_SENSOR_DESCRIPTIONS
        ],
    ]
    async_add_entities(entities, update_before_add=True)


class EcostreamBaseBinarySensor(
    CoordinatorEntity[EcostreamDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Standard mapped binary sensor values from coordinator data."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
        description: EcostreamBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_entity_category = description.entity_category
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )
        self._refresh_state()

    def _refresh_state(self) -> None:
        data = cast(dict[str, Any], self.coordinator.data or {})
        desc = cast(
            EcostreamBinarySensorDescription, self.entity_description
        )
        try:
            self._attr_is_on = desc.value_fn(data)
        except Exception:
            self._attr_is_on = False

    @property
    def available(self) -> bool:  # type: ignore[override]
        data = cast(dict[str, Any], self.coordinator.data or {})
        status = cast(dict[str, Any], data.get("status") or {})
        return bool(status.get("connect_status", 1) == 1)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh_state()
        self.async_write_ha_state()


class EcostreamFilterReplacementWarningBinarySensor(
    CoordinatorEntity[EcostreamDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Filter replacement due warning exposed as binary sensor."""

    _attr_has_entity_name = True
    _attr_name = "Filter Replacement Warning"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: EcostreamDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = (
            f"{entry.entry_id}_filter_replacement_warning_binary"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            manufacturer="BUVA",
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
        )
        self._refresh_state()

    def _refresh_state(self) -> None:
        data = cast(dict[str, object], self.coordinator.data or {})
        config = cast(dict[str, object], data.get("config") or {})
        ts = config.get("filter_datetime")

        if not isinstance(ts, (int, float)) or ts <= 0:
            self._attr_is_on = False
        else:
            self._attr_is_on = time.time() >= float(ts)

    @property
    def available(self) -> bool:  # type: ignore[override]
        data = cast(dict[str, object], self.coordinator.data or {})
        status = cast(dict[str, object], data.get("status") or {})
        return bool(status.get("connect_status", 1) == 1)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh_state()
        self.async_write_ha_state()
