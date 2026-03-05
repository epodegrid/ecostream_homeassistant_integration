from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.components.fan import FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.const import (
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
)
from custom_components.ecostream.fan import EcostreamVentilationFan


def _make_fan(data=None, ws=True, last_update_success=True):
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    coordinator.last_update_success = last_update_success
    coordinator.ws = MagicMock() if ws else None
    if ws:
        coordinator.ws.send_json = AsyncMock()
    coordinator.mark_control_action = MagicMock()
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    with patch.object(
        CoordinatorEntity,
        "__init__",
        lambda self, c: setattr(self, "coordinator", c),
    ):
        fan = EcostreamVentilationFan(coordinator, entry)
    fan.async_write_ha_state = MagicMock()
    return fan, coordinator


# ---------------------------------------------------------------------------
# Basic attributes
# ---------------------------------------------------------------------------


def test_supported_features_includes_turn_on():
    fan, _ = _make_fan()
    assert FanEntityFeature.TURN_ON in fan.supported_features


def test_supported_features_includes_turn_off():
    fan, _ = _make_fan()
    assert FanEntityFeature.TURN_OFF in fan.supported_features


def test_supported_features_includes_set_speed():
    fan, _ = _make_fan()
    assert FanEntityFeature.SET_SPEED in fan.supported_features


def test_unique_id():
    fan, _ = _make_fan()
    assert fan._attr_unique_id == "test_entry_ventilation"


def test_name_attribute():
    fan, _ = _make_fan()
    assert fan._attr_name == "Ventilation"


def test_has_entity_name():
    fan, _ = _make_fan()
    assert fan._attr_has_entity_name is True


def test_should_not_poll():
    fan, _ = _make_fan()
    assert fan._attr_should_poll is False


def test_device_info():
    fan, _ = _make_fan()
    device_info = fan._attr_device_info
    assert device_info is not None
    assert device_info.get("identifiers") == {(DOMAIN, "192.168.1.1")}
    assert device_info.get("manufacturer") == "BUVA"
    assert device_info.get("name") == DEVICE_NAME
    assert device_info.get("model") == DEVICE_MODEL


def test_available_when_last_update_success():
    fan, _ = _make_fan(last_update_success=True)
    assert fan.available is True


def test_not_available_when_last_update_success_false():
    fan, _ = _make_fan(last_update_success=False)
    assert fan.available is False


def test_handle_coordinator_update_writes_state():
    fan, _ = _make_fan(
        {
            "status": {"qset": 100},
            "config": {"capacity_min": 0, "capacity_max": 200},
        }
    )
    fan._handle_coordinator_update()
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


def test_handle_coordinator_update_calculates_percentage():
    fan, _ = _make_fan(
        {
            "status": {"qset": 100},
            "config": {"capacity_min": 0, "capacity_max": 200},
        }
    )
    fan._handle_coordinator_update()
    assert fan.percentage == 50


# ---------------------------------------------------------------------------
# is_on
# ---------------------------------------------------------------------------


def test_is_on_when_qset_positive():
    fan, _ = _make_fan({"status": {"qset": 100}})
    assert fan.is_on is True


def test_is_on_false_when_qset_zero():
    fan, _ = _make_fan({"status": {"qset": 0}})
    assert fan.is_on is False


def test_is_on_false_when_no_data():
    fan, _ = _make_fan()
    assert fan.is_on is False


# ---------------------------------------------------------------------------
# percentage
# ---------------------------------------------------------------------------


def test_percentage_midpoint():
    fan, _ = _make_fan(
        {
            "status": {"qset": 175},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    assert fan.percentage == 30


def test_percentage_at_max():
    fan, _ = _make_fan(
        {
            "status": {"qset": 350},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    assert fan.percentage == 100


def test_percentage_at_min():
    fan, _ = _make_fan(
        {
            "status": {"qset": 100},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    assert fan.percentage == 0


def test_percentage_no_config():
    fan, _ = _make_fan({"status": {"qset": 100}})
    assert fan.percentage is None


def test_percentage_cap_max_equals_min():
    fan, _ = _make_fan(
        {
            "status": {"qset": 100},
            "config": {"capacity_min": 100, "capacity_max": 100},
        }
    )
    assert fan.percentage is None


def test_percentage_clamped_to_0():
    fan, _ = _make_fan(
        {
            "status": {"qset": 50},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    assert fan.percentage == 0


def test_percentage_clamped_to_100():
    fan, _ = _make_fan(
        {
            "status": {"qset": 999},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    assert fan.percentage == 100


# ---------------------------------------------------------------------------
# async_set_percentage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_percentage_sends_correct_qset():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_set_percentage(50)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 100.0


@pytest.mark.asyncio
async def test_set_percentage_no_ws_returns_early():
    fan, _ = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}, ws=False
    )
    await fan.async_set_percentage(50)


@pytest.mark.asyncio
async def test_set_percentage_no_config_returns_early():
    fan, _ = _make_fan()
    await fan.async_set_percentage(50)


@pytest.mark.asyncio
async def test_set_percentage_clamps_below_0():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_set_percentage(-10)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 0.0


@pytest.mark.asyncio
async def test_set_percentage_clamps_above_100():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_set_percentage(200)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 200.0


@pytest.mark.asyncio
async def test_set_percentage_marks_control_action():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_set_percentage(50)
    coordinator.mark_control_action.assert_called_once()


# ---------------------------------------------------------------------------
# async_turn_on / async_turn_off
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_off_sets_percentage_0():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_turn_off()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 0.0


@pytest.mark.asyncio
async def test_turn_on_with_percentage_kwarg():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_turn_on(percentage=50)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 100.0


@pytest.mark.asyncio
async def test_turn_on_without_percentage_uses_stored_percentage():
    fan, coordinator = _make_fan(
        {
            "status": {"qset": 100},
            "config": {"capacity_min": 0, "capacity_max": 200},
        }
    )
    await fan.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 100.0


@pytest.mark.asyncio
async def test_turn_on_defaults_to_30_percent_when_no_stored_percentage():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 60.0  # 30% of 200


@pytest.mark.asyncio
async def test_turn_on_with_kwargs():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_turn_on(percentage=75, extra_arg="ignored")
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 150.0


# ---------------------------------------------------------------------------
# Payload structure validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_percentage_payload_structure():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_set_percentage(50)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert "config" in payload
    assert "man_override_set" in payload["config"]
    assert "man_override_set_time" in payload["config"]
    assert payload["config"]["man_override_set_time"] == 0


@pytest.mark.asyncio
async def test_set_percentage_writes_state_after_send():
    fan, _ = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_set_percentage(50)
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


# ---------------------------------------------------------------------------
# Type casting and error handling
# ---------------------------------------------------------------------------


def test_get_qset_with_string_value():
    fan, _ = _make_fan({"status": {"qset": "150.5"}})
    assert fan._get_qset() == 150.5


def test_get_qset_with_invalid_string():
    fan, _ = _make_fan({"status": {"qset": "invalid"}})
    assert fan._get_qset() == 0.0


def test_get_qset_with_none():
    fan, _ = _make_fan({"status": {"qset": None}})
    assert fan._get_qset() == 0.0


def test_get_capacity_min_with_string_value():
    fan, _ = _make_fan({"config": {"capacity_min": "50"}})
    assert fan._get_capacity_min() == 50.0


def test_get_capacity_min_with_none():
    fan, _ = _make_fan({"config": {"capacity_min": None}})
    assert fan._get_capacity_min() is None


def test_get_capacity_min_with_invalid_string():
    fan, _ = _make_fan({"config": {"capacity_min": "invalid"}})
    assert fan._get_capacity_min() is None


def test_get_capacity_max_with_string_value():
    fan, _ = _make_fan({"config": {"capacity_max": "300"}})
    assert fan._get_capacity_max() == 300.0


def test_get_capacity_max_with_none():
    fan, _ = _make_fan({"config": {"capacity_max": None}})
    assert fan._get_capacity_max() is None


def test_get_capacity_max_with_invalid_string():
    fan, _ = _make_fan({"config": {"capacity_max": "invalid"}})
    assert fan._get_capacity_max() is None


# ---------------------------------------------------------------------------
# Percentage calculation edge cases
# ---------------------------------------------------------------------------


def test_percentage_with_fractional_qset():
    fan, _ = _make_fan(
        {
            "status": {"qset": 175.7},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    # (175.7 - 100) / (350 - 100) * 100 = 75.7 / 250 * 100 = 30.28 → rounds to 30
    assert fan.percentage == 30


def test_percentage_below_minimum():
    fan, _ = _make_fan(
        {
            "status": {"qset": 50},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    assert fan.percentage == 0  # Clamped to 0


def test_percentage_above_maximum():
    fan, _ = _make_fan(
        {
            "status": {"qset": 400},
            "config": {"capacity_min": 100, "capacity_max": 350},
        }
    )
    assert fan.percentage == 100  # Clamped to 100


def test_percentage_with_missing_status():
    fan, _ = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    assert fan.percentage is None


def test_percentage_with_missing_config():
    fan, _ = _make_fan({"status": {"qset": 100}})
    assert fan.percentage is None


def test_percentage_with_missing_qset():
    fan, _ = _make_fan(
        {
            "status": {},
            "config": {"capacity_min": 0, "capacity_max": 200},
        }
    )
    assert fan.percentage == 0  # qset defaults to 0


# ---------------------------------------------------------------------------
# Control action marking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_off_marks_control_action():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_turn_off()
    coordinator.mark_control_action.assert_called_once()


@pytest.mark.asyncio
async def test_turn_on_marks_control_action():
    fan, coordinator = _make_fan(
        {"config": {"capacity_min": 0, "capacity_max": 200}}
    )
    await fan.async_turn_on(percentage=50)
    coordinator.mark_control_action.assert_called_once()
