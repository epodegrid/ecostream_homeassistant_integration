from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecostream.const import (
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    PRESET_HIGH,
    PRESET_LOW,
    PRESET_MID,
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
    entry.options = {}
    with patch.object(
        CoordinatorEntity,
        "__init__",
        lambda self, c: setattr(self, "coordinator", c),
    ):
        fan = EcostreamVentilationFan(coordinator, entry)
    fan.async_write_ha_state = MagicMock()
    return fan, coordinator


def test_supported_features_includes_turn_on():
    fan, _ = _make_fan()
    assert FanEntityFeature.TURN_ON in fan.supported_features


def test_supported_features_includes_turn_off():
    fan, _ = _make_fan()
    assert FanEntityFeature.TURN_OFF in fan.supported_features


def test_supported_features_includes_preset_mode():
    fan, _ = _make_fan()
    assert FanEntityFeature.PRESET_MODE in fan.supported_features


def test_unique_id():
    fan, _ = _make_fan()
    assert fan._attr_unique_id == "test_entry_ventilation"


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
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            },
        }
    )
    fan._handle_coordinator_update()
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


def test_is_on_when_qset_positive():
    fan, _ = _make_fan({"status": {"qset": 100}})
    assert fan.is_on is True


def test_is_on_false_when_qset_zero():
    fan, _ = _make_fan({"status": {"qset": 0}})
    assert fan.is_on is False


def test_is_on_false_when_no_data():
    fan, _ = _make_fan()
    assert fan.is_on is False


@pytest.mark.asyncio
async def test_turn_off_sets_preset_low():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_turn_off()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 90.0


@pytest.mark.asyncio
async def test_turn_on_defaults_to_preset_mid():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_turn_on()
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 180.0


@pytest.mark.asyncio
async def test_turn_on_with_preset_mode():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_turn_on(preset_mode=PRESET_HIGH)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 270.0


@pytest.mark.asyncio
async def test_set_preset_mode_low():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_set_preset_mode(PRESET_LOW)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 90.0


@pytest.mark.asyncio
async def test_set_preset_mode_mid():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_set_preset_mode(PRESET_MID)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 180.0


@pytest.mark.asyncio
async def test_set_preset_mode_high():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_set_preset_mode(PRESET_HIGH)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 270.0


@pytest.mark.asyncio
async def test_set_preset_mode_no_ws_returns_early():
    fan, _ = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        },
        ws=False,
    )
    await fan.async_set_preset_mode(PRESET_MID)


@pytest.mark.asyncio
async def test_set_preset_mode_no_setpoint_returns_early():
    fan, _ = _make_fan({"config": {}})
    await fan.async_set_preset_mode(PRESET_MID)


@pytest.mark.asyncio
async def test_set_preset_mode_marks_control_action():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_set_preset_mode(PRESET_MID)
    coordinator.mark_control_action.assert_called_once()


@pytest.mark.asyncio
async def test_set_preset_mode_writes_state():
    fan, _ = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_set_preset_mode(PRESET_MID)
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


def test_get_qset_with_string_value():
    fan, _ = _make_fan({"status": {"qset": "150.5"}})
    assert fan._get_qset() == 150.5


def test_get_qset_with_invalid_string():
    fan, _ = _make_fan({"status": {"qset": "invalid"}})
    assert fan._get_qset() == 0.0


def test_get_qset_with_none():
    fan, _ = _make_fan({"status": {"qset": None}})
    assert fan._get_qset() == 0.0


def test_get_setpoint_with_string_value():
    fan, _ = _make_fan({"config": {"setpoint_low": "90"}})
    assert fan._get_setpoint(PRESET_LOW) == 90.0


def test_get_setpoint_with_none():
    fan, _ = _make_fan({"config": {"setpoint_low": None}})
    assert fan._get_setpoint(PRESET_LOW) is None


def test_get_setpoint_with_invalid_string():
    fan, _ = _make_fan({"config": {"setpoint_low": "invalid"}})
    assert fan._get_setpoint(PRESET_LOW) is None


def test_calculate_preset_closest_to_low():
    fan, _ = _make_fan(
        {
            "status": {"qset": 95},
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            },
        }
    )
    assert fan._calculate_preset(95) == PRESET_LOW


def test_calculate_preset_closest_to_mid():
    fan, _ = _make_fan(
        {
            "status": {"qset": 175},
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            },
        }
    )
    assert fan._calculate_preset(175) == PRESET_MID


def test_calculate_preset_closest_to_high():
    fan, _ = _make_fan(
        {
            "status": {"qset": 265},
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            },
        }
    )
    assert fan._calculate_preset(265) == PRESET_HIGH


def test_calculate_preset_no_setpoints_returns_none():
    fan, _ = _make_fan({"config": {}})
    assert fan._calculate_preset(100) is None


@pytest.mark.asyncio
async def test_turn_off_marks_control_action():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_turn_off()
    coordinator.mark_control_action.assert_called_once()


@pytest.mark.asyncio
async def test_turn_on_marks_control_action():
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    await fan.async_turn_on()
    coordinator.mark_control_action.assert_called_once()


@pytest.mark.skip(
    reason="Test uses non-existent EcostreamApiClient and mock_config_entry fixture - needs rewrite"
)
async def test_fan_set_percentage(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test setting fan percentage."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.ecostream.EcostreamApiClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(
            mock_config_entry.entry_id
        )
        await hass.async_block_till_done()

    state = hass.states.get("fan.ecostream_192_168_1_1")
    assert state
    assert state.state == STATE_ON

    # Mock the API call
    mock_client.async_set_ventilation_level.return_value = None

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {
            ATTR_ENTITY_ID: "fan.ecostream_192_168_1_1",
            ATTR_PERCENTAGE: 66,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_client.async_set_ventilation_level.assert_called_once_with(2)
