from __future__ import annotations

import logging

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

# Static icon constants (used in entity descriptions only)
ICON_UPTIME = "mdi:timer-outline"
ICON_WIFI = "mdi:wifi"
ICON_RSSI = "mdi:wifi-strength-2"
ICON_TEMP = "mdi:thermometer"
ICON_CO2 = "mdi:molecule-co2"
ICON_TVOC = "mdi:chemical-weapon"
ICON_HUMIDITY = "mdi:water-percent"

# Push key groups
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
