from __future__ import annotations

from datetime import UTC, datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import json
from pathlib import Path
from typing import Any

from .const import (
    CONF_FAST_PUSH_INTERVAL,
    CONF_PUSH_INTERVAL,
    DOMAIN,
)


def _validate_icons() -> dict[str, Any]:
    """Light-weight validation of icons.json structure.

    - Checks if file exists
    - Checks if JSON is valid
    - Checks for required top-level keys
    - Reports basic statistics
    """
    icons_path = Path(__file__).with_name("icons.json")

    if not icons_path.exists():
        return {
            "ok": False,
            "error": "icons_file_missing",
            "path": str(icons_path),
        }

    try:
        raw = icons_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as err:  # invalid JSON
        return {
            "ok": False,
            "error": f"icons_json_error: {err}",
            "path": str(icons_path),
        }
    except OSError as err:
        return {
            "ok": False,
            "error": f"icons_read_error: {err}",
            "path": str(icons_path),
        }

    icons = data.get("icons")
    entities = data.get("entities")

    if not isinstance(icons, dict) or not isinstance(entities, dict):
        return {
            "ok": False,
            "error": "icons_schema_invalid",
            "path": str(icons_path),
            "has_icons_dict": isinstance(icons, dict),
            "has_entities_dict": isinstance(entities, dict),
        }

    # very small sanity stats
    return {
        "ok": True,
        "error": None,
        "path": str(icons_path),
        "icons_count": len(icons),
        "entities_count": len(entities),
        "sample_entities": list(entities.keys())[:10],
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
):
    """Return rich diagnostics for the configuration entry."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Coordinator metadata
    opts = coordinator.options
    data = coordinator.data or {}

    # Extra metadata from coordinator internals (if available)
    ws_state = getattr(coordinator, "ws_state", None)
    last_payload = getattr(coordinator, "last_payload", None)
    reconnects = getattr(coordinator, "ws_reconnects", None)
    last_update = getattr(coordinator, "last_update_success_time", None)

    watchdog_count = None
    if isinstance(data, dict) and "system" in data:
        watchdog_count = data["system"].get("wdg_count")

    # Convert last update to readable string
    if isinstance(last_update, datetime):
        last_update_utc = last_update.astimezone(UTC).isoformat()
        age_seconds = int(
            (datetime.now(UTC) - last_update).total_seconds()
        )
    else:
        last_update_utc = None
        age_seconds = None

    # Try extracting last raw "status" portion
    last_status = data.get("status") if isinstance(data, dict) else None

    # Icons validation
    icons_info = _validate_icons()

    return {
        "entry": entry.as_dict(),

        # -------------------------
        # Coordinator & update logic
        # -------------------------
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_update_utc": last_update_utc,
            "seconds_since_last_update": age_seconds,
            "slow_push_interval": opts.get(CONF_PUSH_INTERVAL),
            "fast_push_interval": opts.get(CONF_FAST_PUSH_INTERVAL),
            "data_keys": list(data.keys()),
        },

        # -------------------------
        # WebSocket State
        # -------------------------
        "websocket": {
            "state": ws_state,
            "reconnect_count": reconnects,
            "last_payload_preview": last_payload,
        },

        # -------------------------
        # System internals
        # -------------------------
        "system": {
            "watchdog_count": watchdog_count,
        },

        # -------------------------
        # Icons diagnostics
        # -------------------------
        "icons": icons_info,

        # -------------------------
        # Raw coordinator data dump
        # -------------------------
        "raw_data": data,

        # -------------------------
        # Only the fast-changing part
        # -------------------------
        "raw_status": last_status,
    }

