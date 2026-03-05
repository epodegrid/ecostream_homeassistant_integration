from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.number import EcostreamQsetNumber


def _make_number(data=None, ws=True):
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
        number = EcostreamQsetNumber(coordinator, entry)
    number.async_write_ha_state = MagicMock()
    return number, coordinator


def test_unique_id():
    number, _ = _make_number()
    assert number._attr_unique_id == "test_entry_qset_number"


def test_default_min_max():
    number, _ = _make_number()
    assert number._attr_native_min_value == 60
    assert number._attr_native_max_value == 350


def test_native_value_from_status():
    number, _ = _make_number({"status": {"qset": 150.0}})
    assert number.native_value == 150.0


def test_native_value_none_when_missing():
    number, _ = _make_number()
    assert number.native_value is None


def test_native_value_none_on_invalid():
    number, _ = _make_number({"status": {"qset": "bad"}})
    assert number.native_value is None


def test_handle_coordinator_update_updates_min_max():
    number, _ = _make_number(
        {"config": {"capacity_min": 80, "capacity_max": 400}}
    )
    number._handle_coordinator_update()
    assert number._attr_native_min_value == 80.0
    assert number._attr_native_max_value == 400.0
    cast(MagicMock, number.async_write_ha_state).assert_called_once()


def test_handle_coordinator_update_ignores_non_numeric():
    number, _ = _make_number(
        {"config": {"capacity_min": "bad", "capacity_max": None}}
    )
    original_min = number._attr_native_min_value
    original_max = number._attr_native_max_value
    number._handle_coordinator_update()
    assert number._attr_native_min_value == original_min
    assert number._attr_native_max_value == original_max


@pytest.mark.asyncio
async def test_set_native_value_sends_payload():
    number, coordinator = _make_number()
    await number.async_set_native_value(200.0)
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"man_override_set": 200.0}}
    )
    coordinator.mark_control_action.assert_called_once()


@pytest.mark.asyncio
async def test_set_native_value_no_ws_returns_early():
    number, coordinator = _make_number(ws=False)
    await number.async_set_native_value(200.0)
    coordinator.mark_control_action.assert_not_called()
