from __future__ import annotations

from datetime import UTC, datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import json
from pathlib import Path
from typing import Any, cast

from .const import (
    CONF_BOOST_DURATION,
    CONF_FILTER_REPLACEMENT_DAYS,
    CONF_PRESET_OVERRIDE_MINUTES,
)


def _validate_icons() -> dict[str, Any]:
    icons_path = Path(__file__).parent / "icons.json"
    if not icons_path.exists():
        return {"ok": False, "error": "icons_file_missing"}
    try:
        raw = icons_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except OSError as exc:
        return {"ok": False, "error": f"icons_read_error: {exc}"}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"icons_json_error: {exc}"}
    icons = data.get("icons")
    entities = data.get("entities")
    if not isinstance(icons, dict) or not isinstance(entities, dict):
        return {
            "ok": False,
            "error": "icons_schema_invalid",
            "has_icons_dict": isinstance(icons, dict),
            "has_entities_dict": isinstance(entities, dict),
        }
    icons_typed: dict[str, Any] = cast(dict[str, Any], icons)
    entities_typed: dict[str, Any] = cast(dict[str, Any], entities)
    return {
        "ok": True,
        "error": None,
        "icons_count": len(icons_typed),
        "entities_count": len(entities_typed),
        "sample_entities": list(entities_typed.keys()),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return rich diagnostics for the configuration entry."""

    coordinator = entry.runtime_data

    # Coordinator metadata
    opts = coordinator.options
    data: dict[str, Any] = cast(dict[str, Any], coordinator.data or {})

    # Extra metadata from coordinator internals (if available)
    ws_state = getattr(coordinator, "ws_state", None)
    last_payload = getattr(coordinator, "last_payload", None)
    reconnects = getattr(coordinator, "ws_reconnects", None)
    last_update = getattr(coordinator, "last_update_success_time", None)

    watchdog_count: Any = None
    if "system" in data:
        system: dict[str, Any] = cast(dict[str, Any], data["system"])
        watchdog_count = system.get("wdg_count")

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
    last_status: Any = data.get("status")

    return {
        "entry": entry.as_dict(),
        # -------------------------
        # Coordinator & update logic
        # -------------------------
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_update_utc": last_update_utc,
            "seconds_since_last_update": age_seconds,
            "filter_replacement_days": opts.get(
                CONF_FILTER_REPLACEMENT_DAYS
            ),
            "preset_override_minutes": opts.get(
                CONF_PRESET_OVERRIDE_MINUTES
            ),
            "boost_duration_minutes": opts.get(CONF_BOOST_DURATION),
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
        # Raw coordinator data dump
        # -------------------------
        "raw_data": data,
        # -------------------------
        # Only the fast-changing part
        # -------------------------
        "raw_status": last_status,
        # -------------------------
        # Icons validation
        # -------------------------
        "icons": _validate_icons(),
    }
