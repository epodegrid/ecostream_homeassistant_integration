from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_ON,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.const import (
    CONF_SUMMER_COMFORT_TEMP,
    CONF_PRESET_OVERRIDE_MINUTES,
    DEFAULT_BOOST_DURATION_MINUTES,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
    PRESET_HIGH,
    PRESET_LOW,
    PRESET_MID,
)
from custom_components.ecostream.switch import (
    async_setup_entry,
    EcostreamBoostSwitch,
    EcostreamBypassSwitch,
    EcostreamPresetSwitch,
    EcostreamScheduleSwitch,
    EcostreamSummerComfortSwitch,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


def _make_entity(EntityClass, data=None, ws=True, **kwargs):
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
        entity = EntityClass(coordinator, entry, **kwargs)
    entity.async_write_ha_state = MagicMock()
    return entity, coordinator


@pytest.mark.asyncio
async def test_switch_async_setup_entry_adds_entities():
    coordinator = MagicMock()
    coordinator.host = "192.168.1.1"
    coordinator.data = {}
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.runtime_data = coordinator

    def _mock_coordinator_entity_init(self, c):
        self.coordinator = c

    with patch.object(
        CoordinatorEntity, "__init__", _mock_coordinator_entity_init
    ):
        add_entities = MagicMock()
        await async_setup_entry(MagicMock(), entry, add_entities)

    add_entities.assert_called_once()
    entities = add_entities.call_args[0][0]
    assert len(entities) == 7


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
    cast(MagicMock, entity.async_write_ha_state).assert_called_once()


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
        {"config": {"sum_com_enabled": True, "sum_com_temp": 22}}
    )


@pytest.mark.asyncio
async def test_summer_comfort_turn_on_uses_option_temp():
    entity, coordinator = _make_entity(EcostreamSummerComfortSwitch)
    entity._entry.options = {CONF_SUMMER_COMFORT_TEMP: 26}
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"sum_com_enabled": True, "sum_com_temp": 26}}
    )


@pytest.mark.asyncio
async def test_summer_comfort_turn_on_invalid_temp_uses_default():
    entity, coordinator = _make_entity(EcostreamSummerComfortSwitch)
    entity._entry.options = {CONF_SUMMER_COMFORT_TEMP: "bad"}
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"sum_com_enabled": True, "sum_com_temp": 22}}
    )


@pytest.mark.asyncio
async def test_summer_comfort_turn_on_out_of_range_uses_default():
    entity, coordinator = _make_entity(EcostreamSummerComfortSwitch)
    entity._entry.options = {CONF_SUMMER_COMFORT_TEMP: 99}
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"sum_com_enabled": True, "sum_com_temp": 22}}
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


def test_bypass_switch_unique_id():
    entity, _ = _make_entity(EcostreamBypassSwitch)
    assert entity.unique_id == "test_entry_bypass_valve"


def test_bypass_switch_is_on_from_position():
    entity, _ = _make_entity(
        EcostreamBypassSwitch, {"status": {"bypass_pos": 100}}
    )
    assert entity.is_on is True


@pytest.mark.asyncio
async def test_bypass_switch_turn_on_sends_payload():
    entity, coordinator = _make_entity(EcostreamBypassSwitch)
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"man_override_bypass": 100}}
    )


@pytest.mark.asyncio
async def test_bypass_switch_turn_off_sends_payload():
    entity, coordinator = _make_entity(EcostreamBypassSwitch)
    await entity.async_turn_off()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"man_override_bypass": 0}}
    )


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
        EcostreamBoostSwitch,
        {"config": {"setpoint_high": 350, "capacity_max": 200}},
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
async def test_boost_turn_on_without_setpoint_high_skips_send():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {}}
    )
    coordinator.boost_duration_minutes = 5
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_boost_turn_on_with_invalid_setpoint_high_skips_send():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {"setpoint_high": "bad"}}
    )
    coordinator.boost_duration_minutes = 5
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_boost_turn_on_no_ws():
    entity, _ = _make_entity(EcostreamBoostSwitch, ws=False)
    await entity.async_turn_on()


@pytest.mark.asyncio
async def test_boost_turn_on_duration_below_1_uses_default():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {"setpoint_high": 350}}
    )
    coordinator.boost_duration_minutes = 0
    await entity.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert (
        payload["config"]["man_override_set_time"]
        == DEFAULT_BOOST_DURATION_MINUTES * 60
    )


@pytest.mark.asyncio
async def test_boost_turn_on_invalid_duration_uses_default():
    entity, coordinator = _make_entity(
        EcostreamBoostSwitch, {"config": {"setpoint_high": 350}}
    )
    coordinator.boost_duration_minutes = "bad"
    await entity.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert (
        payload["config"]["man_override_set_time"]
        == DEFAULT_BOOST_DURATION_MINUTES * 60
    )


def test_boost_handle_update_invalid_timer_sets_off():
    entity, _ = _make_entity(
        EcostreamBoostSwitch,
        {"status": {"override_set_time_left": "bad"}},
    )
    entity._handle_coordinator_update()
    assert entity.is_on is False


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
        EcostreamBoostSwitch, {"config": {"setpoint_high": 350}}
    )
    coordinator.boost_duration_minutes = 15
    await entity.async_turn_on()
    coordinator.mark_control_action.assert_called_once()


# ---------------------------------------------------------------------------
# EcostreamPresetSwitch
# ---------------------------------------------------------------------------


def test_preset_switch_unique_id_low():
    entity, _ = _make_entity(EcostreamPresetSwitch, preset=PRESET_LOW)
    assert entity.unique_id == "test_entry_preset_low"


def test_preset_switch_is_on_matches_qset():
    entity, _ = _make_entity(
        EcostreamPresetSwitch,
        {
            "config": {"setpoint_mid": 180},
            "status": {"qset": 180},
        },
        preset=PRESET_MID,
    )
    assert entity.is_on is True


def test_preset_switch_get_setpoint_unknown_preset():
    entity, _ = _make_entity(
        EcostreamPresetSwitch,
        {"config": {"setpoint_low": 90}},
        preset="unknown",
    )
    assert entity._get_setpoint() is None


def test_preset_switch_get_setpoint_invalid_value():
    entity, _ = _make_entity(
        EcostreamPresetSwitch,
        {"config": {"setpoint_low": "bad"}},
        preset=PRESET_LOW,
    )
    assert entity._get_setpoint() is None


def test_preset_switch_is_active_invalid_qset_returns_false():
    entity, _ = _make_entity(
        EcostreamPresetSwitch,
        {"config": {"setpoint_low": 90}, "status": {"qset": "bad"}},
        preset=PRESET_LOW,
    )
    assert entity.is_on is False


def test_preset_switch_handle_update_writes_state():
    entity, _ = _make_entity(
        EcostreamPresetSwitch,
        {"config": {"setpoint_low": 90}, "status": {"qset": 90}},
        preset=PRESET_LOW,
    )
    entity._handle_coordinator_update()
    cast(MagicMock, entity.async_write_ha_state).assert_called_once()


@pytest.mark.asyncio
async def test_preset_switch_turn_on_without_setpoint_skips_send():
    entity, coordinator = _make_entity(
        EcostreamPresetSwitch,
        {"config": {}},
        preset=PRESET_LOW,
    )
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_apply_config_uses_async_send_config_awaitable():
    entity, coordinator = _make_entity(EcostreamScheduleSwitch)
    coordinator.async_send_config = AsyncMock(return_value=True)
    await entity.async_turn_on()
    coordinator.async_send_config.assert_awaited_once_with(
        {"schedule_enabled": True}, "schedule"
    )


@pytest.mark.asyncio
async def test_preset_switch_turn_on_sends_payload():
    entity, coordinator = _make_entity(
        EcostreamPresetSwitch,
        {"config": {"setpoint_high": 270}},
        preset=PRESET_HIGH,
    )
    entity._entry.options = {CONF_PRESET_OVERRIDE_MINUTES: 30}
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {
            "config": {
                "man_override_set": 270.0,
                "man_override_set_time": 1800,
            }
        }
    )


@pytest.mark.asyncio
async def test_preset_switch_turn_on_uses_default_minutes():
    entity, coordinator = _make_entity(
        EcostreamPresetSwitch,
        {"config": {"setpoint_low": 90}},
        preset=PRESET_LOW,
    )
    await entity.async_turn_on()
    coordinator.ws.send_json.assert_called_once_with(
        {
            "config": {
                "man_override_set": 90.0,
                "man_override_set_time": DEFAULT_PRESET_OVERRIDE_MINUTES
                * 60,
            }
        }
    )


@pytest.mark.asyncio
async def test_preset_switch_turn_off_clears_override():
    entity, coordinator = _make_entity(
        EcostreamPresetSwitch,
        {"config": {"setpoint_low": 90}},
        preset=PRESET_LOW,
    )
    await entity.async_turn_off()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"man_override_set_time": 0}}
    )


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skip(reason="Fixtures not implemented")
async def test_switch_turn_on_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test error handling when turning on switch."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.ecostream.EcostreamApiClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(
            mock_config_entry.entry_id
        )
        await hass.async_block_till_done()

    mock_client.async_set_bypass.side_effect = Exception("Error")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.ecostream_192_168_1_1_bypass"},
            blocking=True,
        )
