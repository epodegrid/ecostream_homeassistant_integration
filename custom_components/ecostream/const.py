from __future__ import annotations

import json
import logging
from pathlib import Path
from homeassistant.util.json import load_json

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecostream"

PLATFORMS: list[str] = [
    "sensor",
    "fan",
    "number",
    "switch",
    "valve",
]

# Config options
CONF_PUSH_INTERVAL = "push_interval"
CONF_FAST_PUSH_INTERVAL = "fast_push_interval"

# Boost
BOOST_QSET = 300
BOOST_OPTIONS = ["5", "10", "15", "30"]
CO2_THRESHOLD = 800
DEFAULT_BOOST_DURATION_MINUTES = 15

# Default push intervals (seconds)
DEFAULT_PUSH_INTERVAL = 2
DEFAULT_FAST_PUSH_INTERVAL = 0.7
FAST_MODE_SECONDS = 20
SLOW_PUSH_INTERVAL = 15

# WebSocket timing
WS_HEARTBEAT_INTERVAL = 10
WS_STALE_TIMEOUT = 30
WS_RECONNECT_INITIAL_DELAY = 5
WS_RECONNECT_MAX_DELAY = 60

# Device info
DEVICE_NAME = "EcoStream"
DEVICE_MODEL = "EcoStream"

# ---------------------------------------------------------
# Load icons.json
# ---------------------------------------------------------
ICON_UPTIME = "mdi:timer-outline"
ICON_WIFI = "mdi:wifi"
ICON_RSSI = "mdi:wifi-strength-2"
ICON_TEMP = "mdi:thermometer"
ICON_CO2 = "mdi:molecule-co2"
ICON_TVOC = "mdi:chemical-weapon"
ICON_HUMIDITY = "mdi:water-percent"

icons_path = Path(__file__).parent / "icons.json"
icon_map = {}

try:
    icons_json = load_json(str(icons_path))
    if isinstance(icons_json, dict):
        icon_map = icons_json.get("icons", {})
    else:
        _LOGGER.warning("icons.json does not contain a valid dictionary")

except Exception as err:
    _LOGGER.warning("Could not load icons.json: %s", err)

# ---------------------------------------------------------
# Push key groups (unchanged)
# ---------------------------------------------------------

FAST_KEYS = {
    "status",
}

SLOW_KEYS = {
    "config",
    "system",
    "comm_wifi",
    "comm_bt",
    "error",
    "debug",
    "ext_module",
}
