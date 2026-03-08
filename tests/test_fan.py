from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any, cast
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

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import (  # type: ignore[import-untyped]
        MockConfigEntry,  # type: ignore[import-not-found]
    )
else:
    MockConfigEntry = Any

from custom_components.ecostream.const import (
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    PRESET_HIGH,
    PRESET_LOW,
    PRESET_MID,
)
from custom_components.ecostream.fan import EcostreamVentilationFan


def _make_fan(
    data: dict[str, Any] | None = None,
    ws: bool = True,
    last_update_success: bool = True,
    entry_options: dict[str, Any] | None = None,
) -> tuple[EcostreamVentilationFan, MagicMock]:
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
    entry.options = entry_options or {}

    def mock_init(self: CoordinatorEntity, c: Any) -> None:
        self.coordinator = c

    with patch.object(
        CoordinatorEntity,
        "__init__",
        mock_init,
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
    assert fan.unique_id == "test_entry_ventilation"


def test_has_entity_name():
    fan, _ = _make_fan()
    assert hasattr(fan, "_attr_has_entity_name")
    assert getattr(fan, "_attr_has_entity_name", False) is True


def test_should_not_poll():
    fan, _ = _make_fan()
    assert fan.should_poll is False


def test_device_info():
    fan, _ = _make_fan()
    device_info = fan.device_info
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
    # Trigger the coordinator update callback directly
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


@pytest.mark.asyncio
async def test_set_qset_uses_default_override_minutes():
    fan, coordinator = _make_fan()
    await fan.async_set_qset(150)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 150.0
    assert payload["config"]["man_override_set_time"] == 3600


@pytest.mark.asyncio
async def test_set_qset_uses_entry_override_minutes():
    fan, coordinator = _make_fan(
        entry_options={"preset_override_minutes": 45}
    )
    await fan.async_set_qset(175)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 175.0
    assert payload["config"]["man_override_set_time"] == 2700


@pytest.mark.asyncio
async def test_set_qset_uses_explicit_override_minutes():
    fan, coordinator = _make_fan(
        entry_options={"preset_override_minutes": 45}
    )
    await fan.async_set_qset(200, override_minutes=10)
    payload = coordinator.ws.send_json.call_args[0][0]
    assert payload["config"]["man_override_set"] == 200.0
    assert payload["config"]["man_override_set_time"] == 600


@pytest.mark.asyncio
async def test_set_qset_no_ws_returns_early():
    fan, _ = _make_fan(ws=False)
    await fan.async_set_qset(120)
    cast(MagicMock, fan.async_write_ha_state).assert_not_called()


def test_get_qset_with_string_value():
    fan, _ = _make_fan({"status": {"qset": "150.5"}})
    assert fan.is_on is True


def test_get_qset_with_invalid_string():
    fan, _ = _make_fan({"status": {"qset": "invalid"}})
    assert fan.is_on is False


def test_get_qset_with_none():
    fan, _ = _make_fan({"status": {"qset": None}})
    assert fan.is_on is False


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


# Additional tests for coverage improvement
def test_get_setpoint_with_invalid_value():
    """Test _get_setpoint when setpoint value cannot be converted to float."""
    fan, _ = _make_fan(
        {
            "config": {
                "setpoint_low": "invalid",
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    assert fan._get_setpoint(PRESET_LOW) is None


def test_get_setpoint_with_none_value():
    """Test _get_setpoint when setpoint value is None."""
    fan, _ = _make_fan(
        {
            "config": {
                "setpoint_low": None,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    assert fan._get_setpoint(PRESET_LOW) is None


def test_get_setpoint_with_invalid_preset():
    """Test _get_setpoint with invalid preset name."""
    fan, _ = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    assert fan._get_setpoint("invalid_preset") is None


@pytest.mark.asyncio
async def test_set_preset_mode_with_async_send_config_awaitable():
    """Test async_set_preset_mode when coordinator has async_send_config that returns awaitable."""
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    coordinator.async_send_config = AsyncMock(return_value=None)

    await fan.async_set_preset_mode(PRESET_MID)

    coordinator.async_send_config.assert_called_once()
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


@pytest.mark.asyncio
async def test_set_preset_mode_with_async_send_config_non_awaitable():
    """Test async_set_preset_mode when coordinator has async_send_config that returns non-awaitable."""
    fan, coordinator = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )
    coordinator.async_send_config = MagicMock(return_value=None)

    await fan.async_set_preset_mode(PRESET_MID)

    coordinator.async_send_config.assert_called_once()
    coordinator.mark_control_action.assert_called_once()
    coordinator.ws.send_json.assert_called_once()
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


@pytest.mark.asyncio
async def test_set_qset_with_async_send_config_awaitable():
    """Test async_set_qset when coordinator has async_send_config that returns awaitable."""
    fan, coordinator = _make_fan()
    coordinator.async_send_config = AsyncMock(return_value=None)

    await fan.async_set_qset(200)

    coordinator.async_send_config.assert_called_once()
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


@pytest.mark.asyncio
async def test_set_qset_with_async_send_config_non_awaitable():
    """Test async_set_qset when coordinator has async_send_config that returns non-awaitable."""
    fan, coordinator = _make_fan()
    coordinator.async_send_config = MagicMock(return_value=None)

    await fan.async_set_qset(200)

    coordinator.async_send_config.assert_called_once()
    coordinator.mark_control_action.assert_called_once()
    coordinator.ws.send_json.assert_called_once()
    cast(MagicMock, fan.async_write_ha_state).assert_called_once()


@pytest.mark.asyncio
async def test_set_qset_stores_calculated_preset():
    """Test that async_set_qset stores the calculated preset mode."""
    fan, _ = _make_fan(
        {
            "config": {
                "setpoint_low": 90,
                "setpoint_mid": 180,
                "setpoint_high": 270,
            }
        }
    )

    await fan.async_set_qset(95)

    assert fan._attr_preset_mode == PRESET_LOW


@pytest.mark.asyncio
async def test_async_setup_entry_registers_service():
    """Test that async_setup_entry registers the set_qset service."""
    import custom_components.ecostream.fan as fan_module
    from custom_components.ecostream.fan import async_setup_entry

    # Reset the global flag for testing
    fan_module._qset_service_registered = False

    coordinator = MagicMock()
    entry = MagicMock(spec=ConfigEntry)
    entry.runtime_data = coordinator
    entry.entry_id = "test_entry"

    hass = MagicMock()

    platform = MagicMock()
    platform.async_register_entity_service = MagicMock()

    with patch(
        "custom_components.ecostream.fan.current_platform"
    ) as mock_platform_module:
        mock_platform_module.get.return_value = platform

        await async_setup_entry(hass, entry, MagicMock())

        platform.async_register_entity_service.assert_called_once()
        call_args = platform.async_register_entity_service.call_args
        assert call_args[0][0] == "set_qset"
        assert "qset" in call_args[0][1]


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
