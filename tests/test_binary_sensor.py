from __future__ import annotations

from pathlib import Path
import sys
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    EcostreamBaseBinarySensor,
    EcostreamBinarySensorDescription,
    EcostreamFilterReplacementWarningBinarySensor,
    _bool_value,  # pyright: ignore[reportPrivateUsage]
    _deep_get,  # pyright: ignore[reportPrivateUsage]
    async_setup_entry,
)


def _make_binary_sensor(
    data: dict[str, Any] | None = None,
) -> EcostreamFilterReplacementWarningBinarySensor:
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    def _mock_coordinator_entity_init(
        self: CoordinatorEntity[Any], c: Any
    ) -> None:
        self.coordinator = c
        self._attr_should_poll = False  # pyright: ignore[reportPrivateUsage]

    with patch.object(
        CoordinatorEntity, "__init__", _mock_coordinator_entity_init
    ):
        entity = EcostreamFilterReplacementWarningBinarySensor(
            coordinator, entry
        )

    entity.async_write_ha_state = MagicMock()
    return entity


def _make_state_binary_sensor(
    description: EcostreamBinarySensorDescription,
    data: dict[str, Any] | None = None,
) -> EcostreamBaseBinarySensor:
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    def _mock_coordinator_entity_init(
        self: CoordinatorEntity[Any], c: Any
    ) -> None:
        self.coordinator = c
        self._attr_should_poll = False  # pyright: ignore[reportPrivateUsage]

    with patch.object(
        CoordinatorEntity, "__init__", _mock_coordinator_entity_init
    ):
        entity = EcostreamBaseBinarySensor(
            coordinator, entry, description
        )

    entity.async_write_ha_state = MagicMock()
    return entity


def test_deep_get_returns_value():
    assert _deep_get({"a": {"b": 1}}, ["a", "b"]) == 1


def test_bool_value_uses_default():
    fn = _bool_value(["x"], default=True)
    assert fn({}) is True


def test_filter_replacement_warning_is_on_when_due():
    sensor = _make_binary_sensor(
        {
            "config": {"filter_datetime": int(time.time()) - 10},
            "status": {"connect_status": 1},
        }
    )
    assert sensor.is_on is True


def test_filter_replacement_warning_is_off_when_not_due():
    sensor = _make_binary_sensor(
        {
            "config": {"filter_datetime": int(time.time()) + 3600},
            "status": {"connect_status": 1},
        }
    )
    assert sensor.is_on is False


def test_filter_replacement_warning_is_off_when_missing_timestamp():
    sensor = _make_binary_sensor({"status": {"connect_status": 1}})
    assert sensor.is_on is False


def test_filter_replacement_warning_available_connected():
    sensor = _make_binary_sensor({"status": {"connect_status": 1}})
    assert sensor.available is True


def test_filter_replacement_warning_available_disconnected():
    sensor = _make_binary_sensor({"status": {"connect_status": 0}})
    assert sensor.available is False


def test_filter_replacement_warning_unique_id():
    sensor = _make_binary_sensor()
    assert (
        sensor.unique_id
        == "test_entry_filter_replacement_warning_binary"
    )


def test_filter_replacement_warning_handle_update_writes_state():
    sensor = _make_binary_sensor()
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()  # pyright: ignore[reportPrivateUsage]
    sensor.async_write_ha_state.assert_called_once()


def test_frost_protection_binary_sensor_on():
    desc = next(
        d
        for d in BINARY_SENSOR_DESCRIPTIONS
        if d.key == "frost_protection_active"
    )
    sensor = _make_state_binary_sensor(
        desc,
        {"status": {"frost_protection": 1, "connect_status": 1}},
    )
    assert sensor.is_on is True


def test_schedule_enabled_binary_sensor_off_default():
    desc = next(
        d
        for d in BINARY_SENSOR_DESCRIPTIONS
        if d.key == "schedule_enabled"
    )
    sensor = _make_state_binary_sensor(
        desc, {"status": {"connect_status": 1}}
    )
    assert sensor.is_on is False


def test_summer_comfort_enabled_binary_sensor_on():
    desc = next(
        d
        for d in BINARY_SENSOR_DESCRIPTIONS
        if d.key == "summer_comfort_enabled"
    )
    sensor = _make_state_binary_sensor(
        desc,
        {
            "config": {"sum_com_enabled": True},
            "status": {"connect_status": 1},
        },
    )
    assert sensor.is_on is True


def test_state_binary_sensor_unique_id():
    desc = EcostreamBinarySensorDescription(
        key="schedule_enabled",
        name="Schedule Enabled",
        value_fn=lambda d: bool(d.get("on")),
    )
    sensor = _make_state_binary_sensor(desc, {"on": True})
    assert sensor.unique_id == "test_entry_schedule_enabled"


@pytest.mark.asyncio
async def test_async_setup_entry_adds_binary_sensor_entity():
    coordinator = MagicMock()
    coordinator.host = "192.168.1.1"
    coordinator.data = {}
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.runtime_data = coordinator
    add_entities = MagicMock()

    def _mock_coordinator_entity_init(
        self: CoordinatorEntity[Any], c: Any
    ) -> None:
        self.coordinator = c
        self._attr_should_poll = False  # pyright: ignore[reportPrivateUsage]

    with patch.object(
        CoordinatorEntity, "__init__", _mock_coordinator_entity_init
    ):
        await async_setup_entry(MagicMock(), entry, add_entities)

    add_entities.assert_called_once()
    entities = add_entities.call_args[0][0]
    assert len(entities) == 1 + len(BINARY_SENSOR_DESCRIPTIONS)
    assert isinstance(
        entities[0], EcostreamFilterReplacementWarningBinarySensor
    )
    assert all(
        isinstance(
            entity,
            (
                EcostreamFilterReplacementWarningBinarySensor,
                EcostreamBaseBinarySensor,
            ),
        )
        for entity in entities
    )
