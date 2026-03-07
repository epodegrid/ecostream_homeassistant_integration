from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.const import (
    BOOST_QSET,
    DEFAULT_BOOST_DURATION_MINUTES,
)
from custom_components.ecostream.switch import (
    EcostreamBoostSwitch,
    EcostreamScheduleSwitch,
    EcostreamSummerComfortSwitch,
)


def _make_entity(EntityClass, data=None, ws=True):
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    coordinator.ws = MagicMock() if ws else None
    if ws:
        coordinator.ws.send_json = AsyncMock()
    coordinator.mark_control_action = MagicMock()
    coordinator.boost_duration_minutes = DEFAULT_BOOST_DURATION_MINUTES
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    with patch.object(
        CoordinatorEntity,
        "__init__",
        lambda self, c: setattr(self, "coordinator", c),
    ):
        entity = EntityClass(coordinator, entry)
    entity.async_write_ha_state = AsyncMock()
    return entity, coordinator


# ---------------------------------------------------------------------------
# EcostreamScheduleSwitch
# ---------------------------------------------------------------------------


def test_schedule_is_on_true():
    entity, _ = _make_entity(
        EcostreamScheduleSwitch, {"config": {"schedule_enabled": True}}
    )
    assert entity.is_on is True


def test_schedule_is_on_false():
    entity, _ = _make_entity(EcostreamScheduleSwitch)
    assert entity.is_on is False


def test_schedule_unique_id():
    entity, _ = _make_entity(EcostreamScheduleSwitch)
    assert entity.unique_id == "test_entry_schedule_enabled"


def test_schedule_handle_update():
    entity, _ = _make_entity(EcostreamScheduleSwitch)
    entity._handle_coordinator_update()
    cast(AsyncMock, entity.async_write_ha_state).assert_called_once()


@pytest.mark.asyncio
async def test_schedule_turn_on():
    entity, coordinator = _make_entity(EcostreamScheduleSwitch)
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"schedule_enabled": True}}
    )


@pytest.mark.asyncio
async def test_schedule_turn_off():
    entity, coordinator = _make_entity(EcostreamScheduleSwitch)
    await entity.async_turn_off()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"schedule_enabled": False}}
    )


@pytest.mark.asyncio
async def test_schedule_no_ws_returns_early():
    entity, _ = _make_entity(EcostreamScheduleSwitch, ws=False)
    await entity.async_turn_on()


@pytest.mark.asyncio
async def test_schedule_marks_control_action():
    entity, coordinator = _make_entity(EcostreamScheduleSwitch)
    await entity.async_turn_on()
    coordinator.mark_control_action.assert_called_once()


# ---------------------------------------------------------------------------
# EcostreamSummerComfortSwitch
# ---------------------------------------------------------------------------


def test_summer_comfort_is_on_true():
    entity, _ = _make_entity(
        EcostreamSummerComfortSwitch,
        {"config": {"sum_com_enabled": True}},
    )
    assert entity.is_on is True


def test_summer_comfort_is_on_false():
    entity, _ = _make_entity(EcostreamSummerComfortSwitch)
    assert entity.is_on is False


def test_summer_comfort_unique_id():
    entity, _ = _make_entity(EcostreamSummerComfortSwitch)
    assert entity.unique_id == "test_entry_summer_comfort"


@pytest.mark.asyncio
async def test_summer_comfort_turn_on():
    entity, coordinator = _make_entity(EcostreamSummerComfortSwitch)
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"sum_com_enabled": True}}
    )


@pytest.mark.asyncio
async def test_summer_comfort_turn_off():
    entity, coordinator = _make_entity(EcostreamSummerComfortSwitch)
    await entity.async_turn_off()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"sum_com_enabled": False}}
    )


@pytest.mark.asyncio
async def test_summer_comfort_no_ws():
    entity, _ = _make_entity(EcostreamSummerComfortSwitch, ws=False)
    await entity.async_turn_on()








# ---------------------------------------------------------------------------
# EcostreamBoostSwitch
# ---------------------------------------------------------------------------


def test_boost_is_on_with_timer():
    entity, _ = _make_entity(
        EcostreamBoostSwitch, {"status": {"override_set_time_left": 60}}
    )
    assert entity.is_on is True


def test_boost_is_on_false_zero():
    entity, _ = _make_entity(
        EcostreamBoostSwitch, {"status": {"override_set_time_left": 0}}
    )
    assert entity.is_on is False


def test_boost_is_on_false_none():
    entity, _ = _make_entity(EcostreamBoostSwitch)
    assert entity.is_on is False


def test_boost_is_on_invalid_value():
    entity, _ = _make_entity(
        EcostreamBoostSwitch,
        {"status": {"override_set_time_left": "bad"}},
    )
    assert entity.is_on is False


def test_boost_unique_id():
    entity, _ = _make_entity(EcostreamBoostSwitch)
    assert entity.unique_id == "test_entry_boost"


@pytest.mark.asyncio
async def test_boost_turn_on_uses_capacity_max():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {"capacity_max": 350}}
    )
    coordinator.boost_duration_minutes = 15
    await entity.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 350.0
    assert payload["config"]["man_override_set_time"] == 900


@pytest.mark.asyncio
async def test_boost_turn_on_prefers_setpoint_high():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch,
        {"config": {"setpoint_high": 400, "capacity_max": 350}},
    )
    coordinator.boost_duration_minutes = 10
    await entity.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 400.0


@pytest.mark.asyncio
async def test_boost_turn_on_fallback_boost_qset():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {}}
    )
    coordinator.boost_duration_minutes = 5
    await entity.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == float(BOOST_QSET)


@pytest.mark.asyncio
async def test_boost_turn_on_no_ws():
    entity, _ = _make_entity(EcostreamBoostSwitch, ws=False)
    await entity.async_turn_on()


@pytest.mark.asyncio
async def test_boost_turn_on_duration_below_1_uses_default():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {"capacity_max": 350}}
    )
    coordinator.boost_duration_minutes = 0
    await entity.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert (
        payload["config"]["man_override_set_time"]
        == DEFAULT_BOOST_DURATION_MINUTES * 60
    )


@pytest.mark.asyncio
async def test_boost_turn_off_clears_timer():
    entity, coordinator = _make_entity(EcostreamBoostSwitch)
    await entity.async_turn_off()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set_time"] == 0


@pytest.mark.asyncio
async def test_boost_turn_off_no_ws():
    entity, _ = _make_entity(EcostreamBoostSwitch, ws=False)
    await entity.async_turn_off()


@pytest.mark.asyncio
async def test_boost_turn_on_marks_control_action():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {"capacity_max": 350}}
    )
    coordinator.boost_duration_minutes = 15
    await entity.async_turn_on()
    coordinator.mark_control_action.assert_called_once()
