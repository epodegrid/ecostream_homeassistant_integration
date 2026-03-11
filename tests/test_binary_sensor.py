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
    EcostreamFilterReplacementWarningBinarySensor,
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
    assert len(entities) == 1
    assert isinstance(
        entities[0], EcostreamFilterReplacementWarningBinarySensor
    )
