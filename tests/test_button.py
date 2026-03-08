from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.button import (
    EcostreamResetFilterButton,
)
from custom_components.ecostream.const import (
    CONF_ALLOW_OVERRIDE_FILTER_DATE,
    CONF_FILTER_REPLACEMENT_DAYS,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
)


def _make_reset_filter_button(
    data=None, ws=True, options=None, use_async_send=False
):
    """Helper to create a reset filter button for testing."""
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.host = "192.168.1.1"
    coordinator.ws = MagicMock() if ws else None
    if ws:
        coordinator.ws.send_json = AsyncMock()

    coordinator.mark_control_action = MagicMock()

    if use_async_send:
        coordinator.async_send_config = AsyncMock()
    else:
        # Make sure async_send_config doesn't exist for fallback tests
        if hasattr(coordinator, "async_send_config"):
            delattr(coordinator, "async_send_config")

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
    coordinator.mark_control_action.assert_called_once()
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
    coordinator.mark_control_action.assert_called_once()
    coordinator.ws.send_json.assert_called_once_with(
        {"config": {"filter_datetime": expected_timestamp}}
    )


@pytest.mark.asyncio
async def test_reset_filter_uses_async_send_config():
    """Test that async_send_config is used when available."""
    options = {
        CONF_ALLOW_OVERRIDE_FILTER_DATE: True,
        CONF_FILTER_REPLACEMENT_DAYS: 90,
    }
    entity, coordinator = _make_reset_filter_button(
        options=options, use_async_send=True
    )

    with patch("time.time", return_value=2000000.0):
        await entity.async_press()

    expected_timestamp = int(2000000.0 + 90 * 86400)
    expected_config = {"filter_datetime": expected_timestamp}

    coordinator.async_send_config.assert_called_once_with(
        expected_config, "reset_filter"
    )
    # When async_send_config is used, ws.send_json should NOT be called
    coordinator.ws.send_json.assert_not_called()
    # mark_control_action should also NOT be called when async_send_config is used
    coordinator.mark_control_action.assert_not_called()


@pytest.mark.asyncio
async def test_reset_filter_no_websocket_returns_early():
    options = {CONF_ALLOW_OVERRIDE_FILTER_DATE: True}
    entity, coordinator = _make_reset_filter_button(
        ws=False, options=options
    )

    await entity.async_press()

    # Should not attempt to send when ws is None
    coordinator.mark_control_action.assert_not_called()


@pytest.mark.asyncio
async def test_reset_filter_override_disabled_returns_early():
    options = {CONF_ALLOW_OVERRIDE_FILTER_DATE: False}
    entity, coordinator = _make_reset_filter_button(options=options)

    await entity.async_press()

    coordinator.ws.send_json.assert_not_called()
    coordinator.mark_control_action.assert_not_called()


@pytest.mark.asyncio
async def test_reset_filter_override_not_set_returns_early():
    entity, coordinator = _make_reset_filter_button(options={})

    await entity.async_press()

    coordinator.ws.send_json.assert_not_called()
    coordinator.mark_control_action.assert_not_called()
