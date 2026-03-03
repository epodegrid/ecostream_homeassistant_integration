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
    icons_path = Path(__file__).parent / "icons.json"
    if not icons_path.exists():
        return {"ok": False, "error": "icons_file_missing"}
    try:
        raw = icons_path.read_text()
    except (OSError, json.JSONDecodeError) as e:
        err_type = "icons_json_error" if isinstance(e, json.JSONDecodeError) else "icons_read_error"
        return {"ok": False, "error": f"{err_type}: {e}"}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"icons_json_error: {e}"}
    icons = data.get("icons")
    entities = data.get("entities")
    has_icons = isinstance(icons, dict)
    has_entities = isinstance(entities, dict)
    if not has_icons or not has_entities:
        return {
            "ok": False,
            "error": "icons_schema_invalid",
            "has_icons_dict": has_icons,
            "has_entities_dict": has_entities,
        }
    return {
        "ok": True,
        "error": None,
        "icons_count": len(icons),
        "entities_count": len(entities),
        "sample_entities": list(entities.keys()),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for the configuration entry."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    opts = coordinator.options
    data = coordinator.data or {}

    ws_state = getattr(coordinator, "ws_state", None)
    last_payload = getattr(coordinator, "last_payload", None)
    reconnects = getattr(coordinator, "ws_reconnects", None)
    last_update = getattr(coordinator, "last_update_success_time", None)

    watchdog_count = None
    if isinstance(data, dict) and "system" in data:
        watchdog_count = data["system"].get("wdg_count")

    if isinstance(last_update, datetime):
        last_update_utc = last_update.astimezone(UTC).isoformat()
        age_seconds = int(
            (datetime.now(UTC) - last_update).total_seconds()
        )
    else:
        last_update_utc = None
        age_seconds = None

    last_status = data.get("status") if isinstance(data, dict) else None

    return {
        "entry": entry.as_dict(),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_update_utc": last_update_utc,
            "seconds_since_last_update": age_seconds,
            "slow_push_interval": opts.get(CONF_PUSH_INTERVAL),
            "fast_push_interval": opts.get(CONF_FAST_PUSH_INTERVAL),
            "data_keys": list(data.keys()),
        },
        "websocket": {
            "state": ws_state,
            "reconnect_count": reconnects,
            "last_payload_preview": last_payload,
        },
        "system": {
            "watchdog_count": watchdog_count,
        },
        "raw_data": data,
        "raw_status": last_status,
    }
