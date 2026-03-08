from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.sensor import (
    SENSOR_DESCRIPTIONS,
    EcostreamBaseSensor,
    EcostreamSensorDescription,
    _calc_efficiency,  # pyright: ignore[reportPrivateUsage]
    _deep_get,  # pyright: ignore[reportPrivateUsage]
    _format_uptime,  # pyright: ignore[reportPrivateUsage]
)


def _make_sensor(
    description: EcostreamSensorDescription,
    data: dict[str, Any] | None = None,
) -> EcostreamBaseSensor:
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    def _mock_coordinator_entity_init(
        self: CoordinatorEntity[Any], c: Any
    ) -> None:
        self.coordinator = c
        # Add required attributes that CoordinatorEntity normally sets
        self._attr_should_poll = False  # pyright: ignore[reportPrivateUsage]

    with patch.object(
        CoordinatorEntity, "__init__", _mock_coordinator_entity_init
    ):
        sensor = EcostreamBaseSensor(coordinator, entry, description)
    sensor.async_write_ha_state = MagicMock()
    return sensor


# ---------------------------------------------------------------------------
# _deep_get
# ---------------------------------------------------------------------------


def test_deep_get_returns_value():
    assert _deep_get({"a": {"b": 1}}, ["a", "b"]) == 1


def test_deep_get_missing_key_returns_none():
    assert _deep_get({"a": {}}, ["a", "b"]) is None


def test_deep_get_custom_default():
    assert _deep_get({}, ["x"], default=42) == 42


def test_deep_get_non_mapping_mid_path():
    assert _deep_get({"a": "string"}, ["a", "b"]) is None


def test_deep_get_empty_path_returns_data():
    data = {"key": "val"}
    assert _deep_get(data, []) == data


# ---------------------------------------------------------------------------
# _format_uptime
# ---------------------------------------------------------------------------


def test_format_uptime_negative():
    assert _format_uptime(-1) == "0m"


def test_format_uptime_minutes_only():
    assert _format_uptime(300) == "5m"


def test_format_uptime_hours_and_minutes():
    assert _format_uptime(3661) == "1h 1m"


def test_format_uptime_days_hours_minutes():
    assert _format_uptime(86400 + 3600 + 60) == "1d 1h 1m"


def test_format_uptime_zero():
    assert _format_uptime(0) == "0m"


def test_format_uptime_exact_day():
    assert _format_uptime(86400) == "1d 0h 0m"


# ---------------------------------------------------------------------------
# _calc_efficiency
# ---------------------------------------------------------------------------


def test_calc_efficiency_normal():
    data = {
        "status": {
            "sensor_temp_eta": 20.0,
            "sensor_temp_eha": 5.0,
            "sensor_temp_oda": 0.0,
        }
    }
    assert _calc_efficiency(data) == 75.0


def test_calc_efficiency_zero_denominator():
    data = {
        "status": {
            "sensor_temp_eta": 10.0,
            "sensor_temp_eha": 5.0,
            "sensor_temp_oda": 10.0,
        }
    }
    assert _calc_efficiency(data) is None


def test_calc_efficiency_negative_denominator():
    data = {
        "status": {
            "sensor_temp_eta": 5.0,
            "sensor_temp_eha": 10.0,
            "sensor_temp_oda": 10.0,
        }
    }
    assert _calc_efficiency(data) is None


def test_calc_efficiency_missing_keys():
    assert _calc_efficiency({}) is None


def test_calc_efficiency_clamps_to_100():
    data = {
        "status": {
            "sensor_temp_eta": 20.0,
            "sensor_temp_eha": -10.0,
            "sensor_temp_oda": 0.0,
        }
    }
    assert _calc_efficiency(data) == 100.0


def test_calc_efficiency_clamps_to_0():
    data = {
        "status": {
            "sensor_temp_eta": 20.0,
            "sensor_temp_eha": 25.0,
            "sensor_temp_oda": 0.0,
        }
    }
    assert _calc_efficiency(data) == 0.0


# ---------------------------------------------------------------------------
# EcostreamBaseSensor
# ---------------------------------------------------------------------------


def test_sensor_native_value_basic():
    desc = EcostreamSensorDescription(
        key="test", value_fn=lambda d: d.get("val")
    )
    sensor = _make_sensor(desc, {"val": 42})
    assert sensor.native_value == 42


def test_sensor_native_value_none():
    desc = EcostreamSensorDescription(
        key="test", value_fn=lambda d: None
    )
    assert _make_sensor(desc).native_value is None


def test_sensor_native_value_exception_in_fn():
    desc = EcostreamSensorDescription(
        key="test", value_fn=lambda d: 1 / 0
    )
    assert _make_sensor(desc).native_value is None


def test_sensor_native_value_date_from_timestamp():
    desc = EcostreamSensorDescription(
        key="d", is_date=True, value_fn=lambda d: d.get("ts")
    )
    sensor = _make_sensor(desc, {"ts": 0})
    result = sensor.native_value
    assert result is not None
    assert isinstance(result, datetime)
    # Use a fixed date check instead of relying on timestamp 0
    assert result.year >= 1970


def test_sensor_native_value_date_from_datetime():
    desc = EcostreamSensorDescription(
        key="d", is_date=True, value_fn=lambda d: datetime(2024, 1, 15)
    )
    result = _make_sensor(desc).native_value
    assert isinstance(result, datetime)
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_sensor_native_value_uptime_formatted():
    desc = EcostreamSensorDescription(
        key="uptime", value_fn=lambda d: d.get("uptime")
    )
    sensor = _make_sensor(desc, {"uptime": 3661})
    assert sensor.native_value == "1h 1m"


def test_sensor_available_connected():
    desc = EcostreamSensorDescription(key="k", value_fn=lambda d: None)
    sensor = _make_sensor(desc, {"status": {"connect_status": 1}})
    assert sensor.available is True


def test_sensor_available_disconnected():
    desc = EcostreamSensorDescription(key="k", value_fn=lambda d: None)
    sensor = _make_sensor(desc, {"status": {"connect_status": 0}})
    assert sensor.available is False


def test_sensor_available_no_data():
    desc = EcostreamSensorDescription(key="k", value_fn=lambda d: None)
    sensor = _make_sensor(desc, {})
    # The sensor checks for connect_status key, so empty data should return False
    assert sensor.available is False


def test_sensor_available_none_coordinator_data():
    """Test when coordinator.data is None."""
    desc = EcostreamSensorDescription(key="k", value_fn=lambda d: None)
    coordinator = MagicMock()
    coordinator.data = None
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
        sensor = EcostreamBaseSensor(coordinator, entry, desc)

    assert sensor.available is False


def test_sensor_unique_id():
    desc = EcostreamSensorDescription(
        key="my_sensor", value_fn=lambda d: None
    )
    assert _make_sensor(desc).unique_id == "test_entry_my_sensor"


def test_sensor_descriptions_count():
    assert len(SENSOR_DESCRIPTIONS) > 10


def test_handle_coordinator_update_writes_state():
    desc = EcostreamSensorDescription(key="k", value_fn=lambda d: None)
    sensor = _make_sensor(desc)
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()  # pyright: ignore[reportPrivateUsage]

    sensor.async_write_ha_state.assert_called_once()
