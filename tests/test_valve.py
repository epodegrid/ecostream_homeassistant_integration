from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.switch import EcostreamBypassSwitch


def _make_bypass_switch(data=None, ws=True):
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
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
        bypass = EcostreamBypassSwitch(coordinator, entry)
    bypass.async_write_ha_state = MagicMock()
    return bypass, coordinator


def test_unique_id():
    bypass, _ = _make_bypass_switch()
    assert bypass.unique_id == "test_entry_bypass_valve"


def test_is_on_true_when_position_above_zero():
    bypass, _ = _make_bypass_switch({"status": {"bypass_pos": 10}})
    assert bypass.is_on is True


def test_is_on_false_when_position_zero():
    bypass, _ = _make_bypass_switch({"status": {"bypass_pos": 0}})
    assert bypass.is_on is False


def test_is_on_false_when_position_missing():
    bypass, _ = _make_bypass_switch({"status": {}})
    assert bypass.is_on is False


def test_is_on_false_when_position_invalid():
    bypass, _ = _make_bypass_switch({"status": {"bypass_pos": "bad"}})
    assert bypass.is_on is False


def test_handle_coordinator_update_writes_state():
    bypass, _ = _make_bypass_switch({"status": {"bypass_pos": 100}})
    bypass._handle_coordinator_update()
    assert bypass.is_on is True
    cast(MagicMock, bypass.async_write_ha_state).assert_called_once()


@pytest.mark.asyncio
async def test_turn_on_sends_open_payload():
    bypass, coordinator = _make_bypass_switch()
    await bypass.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"man_override_bypass": 100}}
    )


@pytest.mark.asyncio
async def test_turn_off_sends_close_payload():
    bypass, coordinator = _make_bypass_switch()
    await bypass.async_turn_off()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"man_override_bypass": 0}}
    )


@pytest.mark.asyncio
async def test_turn_on_marks_control_action():
    bypass, coordinator = _make_bypass_switch()
    await bypass.async_turn_on()
    coordinator.mark_control_action.assert_called_once()


@pytest.mark.asyncio
async def test_turn_on_no_ws_returns_early():
    bypass, _ = _make_bypass_switch(ws=False)
    await bypass.async_turn_on()
