import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path
import pytest
from types import SimpleNamespace
from homeassistant.const import CONF_HOST
from custom_components.ecostream.options_flow import EcostreamOptionsFlow

from custom_components.ecostream.const import (
    CONF_FAST_PUSH_INTERVAL,
    CONF_PUSH_INTERVAL,
    DEFAULT_FAST_PUSH_INTERVAL,
    DEFAULT_PUSH_INTERVAL,
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
            CONF_PUSH_INTERVAL: 90,
            CONF_FAST_PUSH_INTERVAL: 12,
        },
    )
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})

    result = await flow.async_step_init()

    assert result.get("type") == "form"
    assert result.get("step_id") == "init"
    assert result.get("errors") == {}
    assert (result.get("description_placeholders") or {})["host"] == "192.168.1.10"

    data_schema = result.get("data_schema")
    assert callable(data_schema)
    defaults = data_schema({})
    assert defaults[CONF_PUSH_INTERVAL] == 90
    assert defaults[CONF_FAST_PUSH_INTERVAL] == 12


@pytest.mark.asyncio
async def test_async_step_init_shows_form_with_hardcoded_defaults_when_missing():
    entry = _make_entry(data={}, options={})
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})

    result = await flow.async_step_init()

    assert result.get("type") == "form"
    assert (result.get("description_placeholders") or {})["host"] == "EcoStream"

    data_schema = result.get("data_schema")
    assert callable(data_schema)
    defaults = data_schema({})
    assert defaults[CONF_PUSH_INTERVAL] == DEFAULT_PUSH_INTERVAL
    assert defaults[CONF_FAST_PUSH_INTERVAL] == DEFAULT_FAST_PUSH_INTERVAL


@pytest.mark.asyncio
async def test_async_step_init_valid_input_creates_entry_and_updates_options():
    entry = _make_entry(
        data={CONF_HOST: "host.local"},
        options={"preserve_me": True},
    )
    flow = EcostreamOptionsFlow(entry)

    flow.async_create_entry = MagicMock(side_effect=lambda **kwargs: {"type": "create_entry", **kwargs})

    result = await flow.async_step_init(
        {
            CONF_PUSH_INTERVAL: "60",
            CONF_FAST_PUSH_INTERVAL: "10",
        }
    )

    assert result.get("type") == "create_entry"
    assert result.get("title") == "EcoStream Options"
    assert result.get("data", {})["preserve_me"] is True
    assert result.get("data", {})[CONF_PUSH_INTERVAL] == 60
    assert result.get("data", {})[CONF_FAST_PUSH_INTERVAL] == 10


@pytest.mark.asyncio
async def test_async_step_init_push_interval_too_short_returns_error():
    entry = _make_entry(options={CONF_PUSH_INTERVAL: 100, CONF_FAST_PUSH_INTERVAL: 20})
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})

    result = await flow.async_step_init(
        {
            CONF_PUSH_INTERVAL: "29",
            CONF_FAST_PUSH_INTERVAL: "10",
        }
    )

    assert result.get("type") == "form"
    assert result.get("errors") == {"base": "push_interval_too_short"}
    assert flow._options[CONF_PUSH_INTERVAL] == 100
    assert flow._options[CONF_FAST_PUSH_INTERVAL] == 20


@pytest.mark.asyncio
async def test_async_step_init_fast_interval_too_short_returns_error():
    entry = _make_entry(options={CONF_PUSH_INTERVAL: 100, CONF_FAST_PUSH_INTERVAL: 20})
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})

    result = await flow.async_step_init(
        {
            CONF_PUSH_INTERVAL: "30",
            CONF_FAST_PUSH_INTERVAL: "4",
        }
    )

    assert result.get("type") == "form"
    assert result.get("errors") == {"base": "fast_interval_too_short"}
    assert flow._options[CONF_PUSH_INTERVAL] == 100
    assert flow._options[CONF_FAST_PUSH_INTERVAL] == 20


@pytest.mark.asyncio
async def test_async_step_init_invalid_number_returns_error():
    entry = _make_entry(options={})
    flow = EcostreamOptionsFlow(entry)

    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})

    result = await flow.async_step_init(
        {
            CONF_PUSH_INTERVAL: "not-a-number",
            CONF_FAST_PUSH_INTERVAL: "10",
        }
    )

    assert result.get("type") == "form"
    assert result.get("errors") == {"base": "invalid_number"}


def test_async_get_options_flow_returns_instance():
    entry = _make_entry(data={}, options={})
    flow = EcostreamOptionsFlow.async_get_options_flow(entry)

    assert isinstance(flow, EcostreamOptionsFlow)
    assert flow._entry is entry