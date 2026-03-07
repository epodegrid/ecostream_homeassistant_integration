from homeassistant.const import CONF_HOST
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

from custom_components.ecostream.const import (
    CONF_ALLOW_OVERRIDE_FILTER_DATE,
    CONF_BOOST_DURATION,
    CONF_FILTER_REPLACEMENT_DAYS,
    CONF_PRESET_OVERRIDE_MINUTES,
    DEFAULT_BOOST_DURATION_MINUTES,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
)
from custom_components.ecostream.options_flow import (
    EcostreamOptionsFlow,
)

sys.path.append(str(Path(__file__).resolve().parents[1]))


def _make_entry(data=None, options=None):
    entry = MagicMock()
    entry.data = data or {}
    entry.options = options or {}
    return entry


@pytest.mark.asyncio
async def test_async_step_init_shows_form_with_existing_defaults():
    entry = _make_entry(
        data={CONF_HOST: "192.168.1.10"},
        options={
            CONF_FILTER_REPLACEMENT_DAYS: 90,
            CONF_PRESET_OVERRIDE_MINUTES: 30,
            CONF_BOOST_DURATION: 20,
            CONF_ALLOW_OVERRIDE_FILTER_DATE: True,
        },
    )
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    result = await flow.async_step_init()

    assert result.get("type") == "form"
    assert result.get("step_id") == "init"
    assert result.get("errors") == {}
    assert (result.get("description_placeholders") or {})[
        "host"
    ] == "192.168.1.10"

    data_schema = result.get("data_schema")
    assert callable(data_schema)
    defaults = data_schema({})
    assert defaults[CONF_FILTER_REPLACEMENT_DAYS] == 90
    assert defaults[CONF_PRESET_OVERRIDE_MINUTES] == 30
    assert defaults[CONF_BOOST_DURATION] == 20
    assert defaults[CONF_ALLOW_OVERRIDE_FILTER_DATE] is True


@pytest.mark.asyncio
async def test_async_step_init_shows_form_with_hardcoded_defaults_when_missing():
    entry = _make_entry(data={}, options={})
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    result = await flow.async_step_init()

    assert result.get("type") == "form"
    assert (result.get("description_placeholders") or {})[
        "host"
    ] == "EcoStream"

    data_schema = result.get("data_schema")
    assert callable(data_schema)
    defaults = data_schema({})
    assert (
        defaults[CONF_FILTER_REPLACEMENT_DAYS]
        == DEFAULT_FILTER_REPLACEMENT_DAYS
    )
    assert (
        defaults[CONF_PRESET_OVERRIDE_MINUTES]
        == DEFAULT_PRESET_OVERRIDE_MINUTES
    )
    assert (
        defaults[CONF_BOOST_DURATION] == DEFAULT_BOOST_DURATION_MINUTES
    )
    assert defaults[CONF_ALLOW_OVERRIDE_FILTER_DATE] is False


@pytest.mark.asyncio
async def test_async_step_init_valid_input_creates_entry_and_updates_options():
    entry = _make_entry(
        data={CONF_HOST: "host.local"},
        options={"preserve_me": True},
    )
    flow = EcostreamOptionsFlow(entry)

    flow.async_create_entry = MagicMock(
        side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
    )

    result = await flow.async_step_init(
        {
            CONF_FILTER_REPLACEMENT_DAYS: 120,
            CONF_PRESET_OVERRIDE_MINUTES: 45,
            CONF_BOOST_DURATION: 10,
            CONF_ALLOW_OVERRIDE_FILTER_DATE: False,
        }
    )

    assert result.get("type") == "create_entry"
    assert result.get("title") == "EcoStream Options"
    assert result.get("data", {})["preserve_me"] is True
    assert result.get("data", {})[CONF_FILTER_REPLACEMENT_DAYS] == 120
    assert result.get("data", {})[CONF_PRESET_OVERRIDE_MINUTES] == 45
    assert result.get("data", {})[CONF_BOOST_DURATION] == 10
    assert (
        result.get("data", {})[CONF_ALLOW_OVERRIDE_FILTER_DATE] is False
    )


@pytest.mark.asyncio
async def test_async_step_init_filter_days_too_short_returns_error():
    entry = _make_entry(
        options={
            CONF_FILTER_REPLACEMENT_DAYS: 180,
            CONF_PRESET_OVERRIDE_MINUTES: 60,
            CONF_BOOST_DURATION: 15,
        }
    )
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    result = await flow.async_step_init(
        {
            CONF_FILTER_REPLACEMENT_DAYS: 20,  # Too short (< 30)
            CONF_PRESET_OVERRIDE_MINUTES: 60,
            CONF_BOOST_DURATION: 15,
        }
    )

    assert result.get("type") == "form"
    assert result.get("errors") == {"base": "invalid_number"}
    assert flow._options[CONF_FILTER_REPLACEMENT_DAYS] == 180


@pytest.mark.asyncio
async def test_async_step_init_preset_override_too_short_returns_error():
    entry = _make_entry(
        options={
            CONF_FILTER_REPLACEMENT_DAYS: 180,
            CONF_PRESET_OVERRIDE_MINUTES: 60,
            CONF_BOOST_DURATION: 15,
        }
    )
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    result = await flow.async_step_init(
        {
            CONF_FILTER_REPLACEMENT_DAYS: 180,
            CONF_PRESET_OVERRIDE_MINUTES: 3,  # Too short (< 5)
            CONF_BOOST_DURATION: 15,
        }
    )

    assert result.get("type") == "form"
    assert result.get("errors") == {"base": "invalid_number"}
    assert flow._options[CONF_PRESET_OVERRIDE_MINUTES] == 60


@pytest.mark.asyncio
async def test_async_step_init_boost_duration_too_short_returns_error():
    entry = _make_entry(
        options={
            CONF_FILTER_REPLACEMENT_DAYS: 180,
            CONF_PRESET_OVERRIDE_MINUTES: 60,
            CONF_BOOST_DURATION: 15,
        }
    )
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    result = await flow.async_step_init(
        {
            CONF_FILTER_REPLACEMENT_DAYS: 180,
            CONF_PRESET_OVERRIDE_MINUTES: 60,
            CONF_BOOST_DURATION: 3,  # Too short (< 5)
        }
    )

    assert result.get("type") == "form"
    assert result.get("errors") == {"base": "invalid_number"}
    assert flow._options[CONF_BOOST_DURATION] == 15


@pytest.mark.asyncio
async def test_async_step_init_invalid_number_returns_error():
    entry = _make_entry(options={})
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    result = await flow.async_step_init(
        {
            CONF_FILTER_REPLACEMENT_DAYS: "not-a-number",
            CONF_PRESET_OVERRIDE_MINUTES: 60,
            CONF_BOOST_DURATION: 15,
        }
    )

    assert result.get("type") == "form"
    assert result.get("errors") == {"base": "invalid_number"}


def test_async_get_options_flow_returns_instance():
    entry = _make_entry(data={}, options={})
    flow = EcostreamOptionsFlow.async_get_options_flow(entry)

    assert isinstance(flow, EcostreamOptionsFlow)
    assert flow._entry is entry
