from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from custom_components.ecostream.valve import EcostreamBypassValve


def _make_valve(data=None, ws=True):
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
        valve = EcostreamBypassValve(coordinator, entry)
    valve.async_write_ha_state = MagicMock()
    return valve, coordinator


def test_reports_position():
    valve, _ = _make_valve()
    assert valve.reports_position is True

def test_unique_id():
    valve, _ = _make_valve()
    assert valve._attr_unique_id == "test_entry_bypass_valve"

def test_initial_position_is_none():
    valve, _ = _make_valve()
    assert valve.current_valve_position is None

def test_is_open_none_when_position_none():
    valve, _ = _make_valve()
    assert valve.is_open is None

def test_is_closed_none_when_position_none():
    valve, _ = _make_valve()
    assert valve.is_closed is None

def test_is_open_true():
    valve, _ = _make_valve()
    valve._position = 50
    assert valve.is_open is True

def test_is_open_false_at_zero():
    valve, _ = _make_valve()
    valve._position = 0
    assert valve.is_open is False

def test_is_closed_true():
    valve, _ = _make_valve()
    valve._position = 0
    assert valve.is_closed is True

def test_is_opening_false():
    assert _make_valve()[0].is_opening is False

def test_is_closing_false():
    assert _make_valve()[0].is_closing is False

def test_handle_coordinator_update_sets_position():
    valve, _ = _make_valve({"status": {"bypass_pos": 75.4}})
    valve._handle_coordinator_update()
    assert valve._position == 75
    valve.async_write_ha_state.assert_called_once()

def test_handle_coordinator_update_ignores_invalid():
    valve, _ = _make_valve({"status": {"bypass_pos": "bad"}})
    valve._position = 50
    valve._handle_coordinator_update()
    assert valve._position == 50

def test_handle_coordinator_update_no_bypass_pos_unchanged():
    valve, _ = _make_valve({"status": {}})
    valve._position = 50
    valve._handle_coordinator_update()
    assert valve._position == 50

@pytest.mark.asyncio
async def test_open_valve_sends_100():
    valve, coordinator = _make_valve()
    await valve.async_open_valve()
    coordinator.ws.send_json.assert_called_once_with({"config": {"man_override_bypass": 100}})
    assert valve._position == 100

@pytest.mark.asyncio
async def test_close_valve_sends_0():
    valve, coordinator = _make_valve()
    await valve.async_close_valve()
    coordinator.ws.send_json.assert_called_once_with({"config": {"man_override_bypass": 0}})
    assert valve._position == 0

@pytest.mark.asyncio
async def test_set_position_clamps_above_100():
    valve, coordinator = _make_valve()
    await valve.async_set_valve_position(150)
    assert coordinator.ws.send_json.call_args[0][0]["config"]["man_override_bypass"] == 100

@pytest.mark.asyncio
async def test_set_position_clamps_below_0():
    valve, coordinator = _make_valve()
    await valve.async_set_valve_position(-10)
    assert coordinator.ws.send_json.call_args[0][0]["config"]["man_override_bypass"] == 0

@pytest.mark.asyncio
async def test_set_position_no_ws_returns_early():
    valve, _ = _make_valve(ws=False)
    await valve.async_set_valve_position(50)

@pytest.mark.asyncio
async def test_set_position_marks_control_action():
    valve, coordinator = _make_valve()
    await valve.async_set_valve_position(50)
    coordinator.mark_control_action.assert_called_once()

@pytest.mark.asyncio
async def test_set_position_updates_local_state():
    valve, _ = _make_valve()
    await valve.async_set_valve_position(60)
    assert _make_valve()[0]._position is None
    valve_local, _ = _make_valve()
    await valve_local.async_set_valve_position(60)
    assert valve_local._position == 60
    valve_local.async_write_ha_state.assert_called_once()