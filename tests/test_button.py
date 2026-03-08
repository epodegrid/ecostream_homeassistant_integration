from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.button import (
    EcostreamPresetButton,
    EcostreamResetFilterButton,
)
from custom_components.ecostream.const import (
    CONF_ALLOW_OVERRIDE_FILTER_DATE,
    CONF_FILTER_REPLACEMENT_DAYS,
    CONF_PRESET_OVERRIDE_MINUTES,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
    PRESET_HIGH,
    PRESET_LOW,
    PRESET_MID,
)


def _make_preset_button(preset: str, data=None, ws=True, options=None):
    """Helper to create a preset button for testing."""
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    coordinator.ws = MagicMock() if ws else None
    if ws:
        coordinator.ws.send_json = AsyncMock()
    coordinator.mark_control_action = MagicMock()

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.options = options or {}

    with patch.object(
        CoordinatorEntity,
        "__init__",
        lambda self, c: setattr(self, "coordinator", c),
    ):
        entity = EcostreamPresetButton(coordinator, entry, preset)

    return entity, coordinator


def _make_reset_filter_button(data=None, ws=True, options=None):
    """Helper to create a reset filter button for testing."""
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    coordinator.ws = MagicMock() if ws else None
    if ws:
        coordinator.ws.send_json = AsyncMock()

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.options = options or {}

    with patch.object(
        CoordinatorEntity,
        "__init__",
        lambda self, c: setattr(self, "coordinator", c),
    ):
        entity = EcostreamResetFilterButton(coordinator, entry)

    return entity, coordinator


# ---------------------------------------------------------------------------
# EcostreamPresetButton - Basic Properties
# ---------------------------------------------------------------------------


def test_preset_button_unique_id_low():
    entity, _ = _make_preset_button(PRESET_LOW)
    assert entity._attr_unique_id == "test_entry_preset_low"


def test_preset_button_unique_id_mid():
    entity, _ = _make_preset_button(PRESET_MID)
    assert entity._attr_unique_id == "test_entry_preset_mid"


def test_preset_button_unique_id_high():
    entity, _ = _make_preset_button(PRESET_HIGH)
    assert entity._attr_unique_id == "test_entry_preset_high"


def test_preset_button_name():
    entity, _ = _make_preset_button(PRESET_LOW)
    assert entity._attr_name == PRESET_LOW


def test_preset_button_icon():
    entity, _ = _make_preset_button(PRESET_LOW)
    assert entity._attr_icon == "mdi:fan"


# ---------------------------------------------------------------------------
# EcostreamPresetButton - Setpoint Retrieval
# ---------------------------------------------------------------------------


def test_get_setpoint_low():
    data = {"config": {"setpoint_low": 100.0}}
    entity, _ = _make_preset_button(PRESET_LOW, data=data)
    assert entity._get_setpoint() == 100.0


def test_get_setpoint_mid():
    data = {"config": {"setpoint_mid": 200.0}}
    entity, _ = _make_preset_button(PRESET_MID, data=data)
    assert entity._get_setpoint() == 200.0


def test_get_setpoint_high():
    data = {"config": {"setpoint_high": 300.0}}
    entity, _ = _make_preset_button(PRESET_HIGH, data=data)
    assert entity._get_setpoint() == 300.0


def test_get_setpoint_missing_config():
    entity, _ = _make_preset_button(PRESET_LOW, data={})
    assert entity._get_setpoint() is None


def test_get_setpoint_missing_key():
    data = {"config": {}}
    entity, _ = _make_preset_button(PRESET_LOW, data=data)
    assert entity._get_setpoint() is None


def test_get_setpoint_invalid_value():
    data = {"config": {"setpoint_low": "invalid"}}
    entity, _ = _make_preset_button(PRESET_LOW, data=data)
    assert entity._get_setpoint() is None


def test_get_setpoint_none_value():
    data = {"config": {"setpoint_low": None}}
    entity, _ = _make_preset_button(PRESET_LOW, data=data)
    assert entity._get_setpoint() is None


# ---------------------------------------------------------------------------
# EcostreamPresetButton - Extra State Attributes
# ---------------------------------------------------------------------------


def test_extra_state_attributes_with_setpoint():
    data = {"config": {"setpoint_low": 150.0}}
    entity, _ = _make_preset_button(PRESET_LOW, data=data)
    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["setpoint"] == 150.0
    assert attrs["unit"] == "m³/h"


def test_extra_state_attributes_no_setpoint():
    entity, _ = _make_preset_button(PRESET_LOW, data={})
    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["setpoint"] is None
    assert attrs["unit"] == "m³/h"


# ---------------------------------------------------------------------------
# EcostreamPresetButton - Press Action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_press_sends_correct_payload():
    data = {"config": {"setpoint_low": 100.0}}
    options = {CONF_PRESET_OVERRIDE_MINUTES: 60}
    entity, coordinator = _make_preset_button(
        PRESET_LOW, data=data, options=options
    )

    await entity.async_press()

    coordinator.ws.send_json.assert_called_once_with(
        {
            "config": {
                "man_override_set": 100.0,
                "man_override_set_time": 3600,  # 60 minutes * 60 seconds
            }
        }
    )


@pytest.mark.asyncio
async def test_press_uses_default_override_minutes():
    data = {"config": {"setpoint_mid": 200.0}}
    entity, coordinator = _make_preset_button(PRESET_MID, data=data)

    await entity.async_press()

    expected_seconds = DEFAULT_PRESET_OVERRIDE_MINUTES * 60
    coordinator.ws.send_json.assert_called_once_with(
        {
            "config": {
                "man_override_set": 200.0,
                "man_override_set_time": expected_seconds,
            }
        }
    )


@pytest.mark.asyncio
async def test_press_marks_control_action():
    data = {"config": {"setpoint_high": 300.0}}
    entity, coordinator = _make_preset_button(PRESET_HIGH, data=data)

    await entity.async_press()

    coordinator.mark_control_action.assert_called_once()


@pytest.mark.asyncio
async def test_press_no_websocket_returns_early():
    data = {"config": {"setpoint_low": 100.0}}
    entity, coordinator = _make_preset_button(
        PRESET_LOW, data=data, ws=False
    )

    await entity.async_press()

    # Should not have called mark_control_action when ws is missing
    coordinator.mark_control_action.assert_not_called()


@pytest.mark.asyncio
async def test_press_no_setpoint_returns_early():
    entity, coordinator = _make_preset_button(PRESET_LOW, data={})

    await entity.async_press()

    coordinator.ws.send_json.assert_not_called()
    coordinator.mark_control_action.assert_not_called()


# ---------------------------------------------------------------------------
# EcostreamResetFilterButton - Basic Properties
# ---------------------------------------------------------------------------


def test_reset_filter_unique_id():
    entity, _ = _make_reset_filter_button()
    assert entity._attr_unique_id == "test_entry_reset_filter"


def test_reset_filter_translation_key():
    entity, _ = _make_reset_filter_button()
    assert entity._attr_translation_key == "reset_filter"


def test_reset_filter_icon():
    entity, _ = _make_reset_filter_button()
    assert entity._attr_icon == "mdi:air-filter"


# ---------------------------------------------------------------------------
# EcostreamResetFilterButton - Press Action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_filter_press_sends_correct_payload():
    options = {
        CONF_ALLOW_OVERRIDE_FILTER_DATE: True,
        CONF_FILTER_REPLACEMENT_DAYS: 180,
    }
    entity, coordinator = _make_reset_filter_button(options=options)

    with patch("time.time", return_value=1000000.0):
        await entity.async_press()

    expected_timestamp = int(1000000.0 + 180 * 86400)
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"filter_datetime": expected_timestamp}}
    )


@pytest.mark.asyncio
async def test_reset_filter_uses_default_days():
    options = {CONF_ALLOW_OVERRIDE_FILTER_DATE: True}
    entity, coordinator = _make_reset_filter_button(options=options)

    with patch("time.time", return_value=1000000.0):
        await entity.async_press()

    expected_timestamp = int(
        1000000.0 + DEFAULT_FILTER_REPLACEMENT_DAYS * 86400
    )
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"filter_datetime": expected_timestamp}}
    )


@pytest.mark.asyncio
async def test_reset_filter_no_websocket_returns_early():
    options = {CONF_ALLOW_OVERRIDE_FILTER_DATE: True}
    entity, coordinator = _make_reset_filter_button(
        ws=False, options=options
    )

    await entity.async_press()

    # Should not attempt to send when ws is None


@pytest.mark.asyncio
async def test_reset_filter_override_disabled_returns_early():
    options = {CONF_ALLOW_OVERRIDE_FILTER_DATE: False}
    entity, coordinator = _make_reset_filter_button(options=options)

    await entity.async_press()

    coordinator.ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_reset_filter_override_not_set_returns_early():
    entity, coordinator = _make_reset_filter_button(options={})

    await entity.async_press()

    coordinator.ws.send_json.assert_not_called()
