from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.fan import FanEntityFeature

from custom_components.ecostream.fan import EcostreamVentilationFan


def _make_fan(data=None, ws=True):
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    coordinator.ws = MagicMock() if ws else None
    if ws:
        coordinator.ws.send_json = AsyncMock()
    coordinator.mark_control_action = MagicMock()
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    with patch.object(CoordinatorEntity, "__init__", lambda self, c: setattr(self, "coordinator", c)):
        fan = EcostreamVentilationFan(coordinator, entry)
    fan.async_write_ha_state = MagicMock()
    return fan, coordinator


def test_supported_features_includes_set_percentage():
    fan, _ = _make_fan()
    assert FanEntityFeature.SET_PERCENTAGE in fan.supported_features

def test_unique_id():
    fan, _ = _make_fan()
    assert fan._attr_unique_id == "test_entry_ventilation"

def test_handle_coordinator_update_writes_state():
    fan, _ = _make_fan()
    fan._handle_coordinator_update()
    fan.async_write_ha_state.assert_called_once()


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
    fan, _ = _make_fan({"status": {"qset": 175}, "config": {"capacity_min": 100, "capacity_max": 350}})
    assert fan.percentage == 30

def test_percentage_at_max():
    fan, _ = _make_fan({"status": {"qset": 350}, "config": {"capacity_min": 100, "capacity_max": 350}})
    assert fan.percentage == 100

def test_percentage_at_min():
    fan, _ = _make_fan({"status": {"qset": 100}, "config": {"capacity_min": 100, "capacity_max": 350}})
    assert fan.percentage == 0

def test_percentage_no_config():
    fan, _ = _make_fan({"status": {"qset": 100}})
    assert fan.percentage is None

def test_percentage_cap_max_equals_min():
    fan, _ = _make_fan({"status": {"qset": 100}, "config": {"capacity_min": 100, "capacity_max": 100}})
    assert fan.percentage is None

def test_percentage_clamped_to_0():
    fan, _ = _make_fan({"status": {"qset": 50}, "config": {"capacity_min": 100, "capacity_max": 350}})
    assert fan.percentage == 0

def test_percentage_clamped_to_100():
    fan, _ = _make_fan({"status": {"qset": 999}, "config": {"capacity_min": 100, "capacity_max": 350}})
    assert fan.percentage == 100




# ---------------------------------------------------------------------------
# async_set_percentage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_percentage_sends_correct_qset():
    fan, coordinator = _make_fan({"config": {"capacity_min": 0, "capacity_max": 200}})
    await fan.async_set_percentage(50)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 100.0

@pytest.mark.asyncio
async def test_set_percentage_no_ws_returns_early():
    fan, coordinator = _make_fan({"config": {"capacity_min": 0, "capacity_max": 200}}, ws=False)
    await fan.async_set_percentage(50)

@pytest.mark.asyncio
async def test_set_percentage_no_config_returns_early():
    fan, coordinator = _make_fan()
    await fan.async_set_percentage(50)
    coordinator.ws.send_json.assert_not_called()

@pytest.mark.asyncio
async def test_set_percentage_clamps_below_0():
    fan, coordinator = _make_fan({"config": {"capacity_min": 0, "capacity_max": 200}})
    await fan.async_set_percentage(-10)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 0.0

@pytest.mark.asyncio
async def test_set_percentage_clamps_above_100():
    fan, coordinator = _make_fan({"config": {"capacity_min": 0, "capacity_max": 200}})
    await fan.async_set_percentage(200)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 200.0

@pytest.mark.asyncio
async def test_set_percentage_marks_control_action():
    fan, coordinator = _make_fan({"config": {"capacity_min": 0, "capacity_max": 200}})
    await fan.async_set_percentage(50)
    coordinator.mark_control_action.assert_called_once()


# ---------------------------------------------------------------------------
# async_turn_on / async_turn_off
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_turn_off_sets_percentage_0():
    fan, coordinator = _make_fan({"config": {"capacity_min": 0, "capacity_max": 200}})
    await fan.async_turn_off()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 0.0

@pytest.mark.asyncio
async def test_turn_on_with_percentage_kwarg():
    fan, coordinator = _make_fan({"config": {"capacity_min": 0, "capacity_max": 200}})
    await fan.async_turn_on(percentage=50)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 100.0
