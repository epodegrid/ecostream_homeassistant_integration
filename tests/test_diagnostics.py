from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import json
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

sys.path.append(str(Path(__file__).resolve().parents[1]))

from custom_components.ecostream.const import DOMAIN, CONF_FAST_PUSH_INTERVAL, CONF_PUSH_INTERVAL
from custom_components.ecostream.diagnostics import _validate_icons, async_get_config_entry_diagnostics


class TestValidateIcons:
    """Tests for _validate_icons function."""

    def test_icons_file_missing(self):
        """Test when icons.json file does not exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = _validate_icons()
            assert result["ok"] is False
            assert result["error"] == "icons_file_missing"

    def test_icons_json_decode_error(self):
        """Test when icons.json has invalid JSON."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                result = _validate_icons()
                assert result["ok"] is False
                assert "icons_json_error" in result["error"]

    def test_icons_read_os_error(self):
        """Test when icons.json cannot be read due to OS error."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", side_effect=OSError("read error")):
                result = _validate_icons()
                assert result["ok"] is False
                assert "icons_read_error" in result["error"]

    def test_icons_schema_invalid_missing_keys(self):
        """Test when icons.json is missing required top-level keys."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value='{"other": "data"}'):
                result = _validate_icons()
                assert result["ok"] is False
                assert result["error"] == "icons_schema_invalid"
                assert result["has_icons_dict"] is False
                assert result["has_entities_dict"] is False

    def test_icons_schema_invalid_wrong_types(self):
        """Test when icons or entities are not dicts."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value='{"icons": [], "entities": "invalid"}'):
                result = _validate_icons()
                assert result["ok"] is False
                assert result["error"] == "icons_schema_invalid"

    def test_icons_validation_success(self):
        """Test successful icons.json validation."""
        test_data = {
            "icons": {"icon1": "data1", "icon2": "data2"},
            "entities": {"entity1": {}, "entity2": {}, "entity3": {}},
        }
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(test_data)):
                result = _validate_icons()
                assert result["ok"] is True
                assert result["error"] is None
                assert result["icons_count"] == 2
                assert result["entities_count"] == 3
                assert len(result["sample_entities"]) == 3


class TestAsyncGetConfigEntryDiagnostics:
    """Tests for async_get_config_entry_diagnostics function."""

    @pytest.mark.asyncio
    async def test_basic_diagnostics(self):
        """Test basic diagnostics gathering."""
        hass = AsyncMock(spec=HomeAssistant)
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.as_dict.return_value = {"entry_id": "test_entry_id"}

        coordinator = MagicMock()
        coordinator.options = {}
        coordinator.data = {"system": {"wdg_count": 5}}
        coordinator.last_update_success = True
        coordinator.ws_state = "connected"
        coordinator.ws_reconnects = 2
        coordinator.last_payload = None
        coordinator.last_update_success_time = None

        hass.data = {DOMAIN: {"test_entry_id": coordinator}}

        with patch("custom_components.ecostream.diagnostics._validate_icons", return_value={"ok": True}):
            result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["entry"]["entry_id"] == "test_entry_id"
        assert result["coordinator"]["last_update_success"] is True
        assert result["websocket"]["state"] == "connected"
        assert result["system"]["watchdog_count"] == 5

    @pytest.mark.asyncio
    async def test_diagnostics_with_timestamp(self):
        """Test diagnostics with valid timestamp."""
        hass = AsyncMock(spec=HomeAssistant)
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry"
        entry.as_dict.return_value = {}

        now_utc = datetime.now(timezone.utc)
        coordinator = MagicMock()
        coordinator.options = {CONF_PUSH_INTERVAL: 60, CONF_FAST_PUSH_INTERVAL: 5}
        coordinator.data = {}
        coordinator.last_update_success = True
        coordinator.ws_state = None
        coordinator.ws_reconnects = None
        coordinator.last_payload = None
        coordinator.last_update_success_time = now_utc

        hass.data = {DOMAIN: {"test_entry": coordinator}}

        with patch("custom_components.ecostream.diagnostics._validate_icons", return_value={"ok": True}):
            result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["coordinator"]["last_update_utc"] is not None
        assert result["coordinator"]["seconds_since_last_update"] == 0
        assert result["coordinator"]["slow_push_interval"] == 60
        assert result["coordinator"]["fast_push_interval"] == 5

    @pytest.mark.asyncio
    async def test_diagnostics_with_raw_status(self):
        """Test diagnostics includes raw status data."""
        hass = AsyncMock(spec=HomeAssistant)
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry"
        entry.as_dict.return_value = {}

        coordinator = MagicMock()
        coordinator.options = {}
        coordinator.data = {"status": {"temp": 25, "humidity": 60}}
        coordinator.last_update_success = False
        coordinator.ws_state = None
        coordinator.ws_reconnects = None
        coordinator.last_payload = None
        coordinator.last_update_success_time = None

        hass.data = {DOMAIN: {"test_entry": coordinator}}

        with patch("custom_components.ecostream.diagnostics._validate_icons", return_value={"ok": True}):
            result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["raw_status"] == {"temp": 25, "humidity": 60}
        assert result["raw_data"] == {"status": {"temp": 25, "humidity": 60}}