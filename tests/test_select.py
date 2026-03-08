from __future__ import annotations

from pathlib import Path
import sys
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ecostream.const import (
    BOOST_OPTIONS,
    DEFAULT_BOOST_DURATION_MINUTES,
)
from custom_components.ecostream.select import (
    EcostreamBoostDurationSelect,
)


def _make_select(coordinator_boost_duration: int | None = None):
    """Helper to create a boost duration select for testing."""
    coordinator = MagicMock()
    coordinator.host = "192.168.1.1"

    if coordinator_boost_duration is not None:
        coordinator.boost_duration_minutes = coordinator_boost_duration

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    with patch.object(
        CoordinatorEntity,
        "__init__",
        lambda self, c: setattr(self, "coordinator", c),  # type: ignore[misc]
    ):
        entity = EcostreamBoostDurationSelect(coordinator, entry)

    entity.async_write_ha_state = MagicMock()

    return entity, coordinator


def _async_write_state_mock(
    entity: EcostreamBoostDurationSelect,
) -> MagicMock:
    """Return async_write_ha_state as a MagicMock for typed assertions."""
    return cast(MagicMock, entity.async_write_ha_state)


# ---------------------------------------------------------------------------
# Basic Properties
# ---------------------------------------------------------------------------


def test_unique_id():
    entity, _ = _make_select()
    assert entity._attr_unique_id == "test_entry_boost_duration"


def test_translation_key():
    entity, _ = _make_select()
    assert entity._attr_translation_key == "boost_duration"


def test_icon():
    entity, _ = _make_select()
    assert entity._attr_icon == "mdi:timer-outline"


def test_options():
    entity, _ = _make_select()
    assert entity._attr_options == BOOST_OPTIONS
    # Verify common values are in options
    assert "5" in BOOST_OPTIONS
    assert "15" in BOOST_OPTIONS
    assert "30" in BOOST_OPTIONS


def test_has_entity_name():
    entity, _ = _make_select()
    assert entity._attr_has_entity_name is True


# ---------------------------------------------------------------------------
# Current Option
# ---------------------------------------------------------------------------


def test_current_option_returns_coordinator_value():
    entity, _ = _make_select(coordinator_boost_duration=30)
    assert entity.current_option == "30"


def test_current_option_returns_default_when_not_set():
    entity, coordinator = _make_select()
    # Don't set boost_duration_minutes attribute
    delattr(coordinator, "boost_duration_minutes")

    assert entity.current_option == str(DEFAULT_BOOST_DURATION_MINUTES)


def test_current_option_converts_to_string():
    entity, _ = _make_select(coordinator_boost_duration=60)
    result = entity.current_option
    assert isinstance(result, str)
    assert result == "60"


# ---------------------------------------------------------------------------
# Select Option
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_select_option_updates_coordinator():
    entity, coordinator = _make_select()

    await entity.async_select_option("30")

    assert coordinator.boost_duration_minutes == 30


@pytest.mark.asyncio
async def test_select_option_writes_state():
    entity, _ = _make_select()

    await entity.async_select_option("15")

    _async_write_state_mock(entity).assert_called_once()


@pytest.mark.asyncio
async def test_select_option_handles_all_valid_options():
    entity, coordinator = _make_select()

    for option in BOOST_OPTIONS:
        await entity.async_select_option(option)
        assert coordinator.boost_duration_minutes == int(option)


@pytest.mark.asyncio
async def test_select_option_invalid_value_returns_early():
    entity, coordinator = _make_select()
    initial_value = 15
    coordinator.boost_duration_minutes = initial_value

    await entity.async_select_option("invalid")

    # Should not change the value
    assert coordinator.boost_duration_minutes == initial_value
    _async_write_state_mock(entity).assert_not_called()


@pytest.mark.asyncio
async def test_select_option_non_numeric_string():
    entity, coordinator = _make_select()
    coordinator.boost_duration_minutes = 20

    await entity.async_select_option("abc")

    # Should not change the value
    assert coordinator.boost_duration_minutes == 20
    _async_write_state_mock(entity).assert_not_called()


@pytest.mark.asyncio
async def test_select_option_empty_string():
    entity, coordinator = _make_select()
    coordinator.boost_duration_minutes = 25

    await entity.async_select_option("")

    # Should not change the value
    assert coordinator.boost_duration_minutes == 25
    _async_write_state_mock(entity).assert_not_called()


@pytest.mark.asyncio
async def test_select_option_converts_string_to_int():
    entity, coordinator = _make_select()

    await entity.async_select_option("45")

    # Should store as int, not string
    assert coordinator.boost_duration_minutes == 45
    assert isinstance(coordinator.boost_duration_minutes, int)
