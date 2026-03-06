from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecostream"

PLATFORMS: list[str] = [
    "sensor",
    "fan",
    "number",
    "select",
    "switch",
    "valve",
]

# Config options
CONF_PUSH_INTERVAL = "push_interval"
CONF_FAST_PUSH_INTERVAL = "fast_push_interval"
CONF_FILTER_REPLACEMENT_DAYS = "filter_replacement_days"
CONF_PRESET_LOW_PCT = "preset_low_pct"
CONF_PRESET_MID_PCT = "preset_mid_pct"
CONF_PRESET_HIGH_PCT = "preset_high_pct"

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

# Default options
DEFAULT_FILTER_REPLACEMENT_DAYS = 180
DEFAULT_PRESET_LOW_PCT = 30
DEFAULT_PRESET_MID_PCT = 60
DEFAULT_PRESET_HIGH_PCT = 100

# Fan presets
PRESET_LOW = "low"
PRESET_MID = "mid"
PRESET_HIGH = "high"
PRESET_MODES = [PRESET_LOW, PRESET_MID, PRESET_HIGH]

# WebSocket timing
WS_HEARTBEAT_INTERVAL = 10
WS_STALE_TIMEOUT = 30
WS_RECONNECT_INITIAL_DELAY = 5
WS_RECONNECT_MAX_DELAY = 60

# Device info
DEVICE_NAME = "EcoStream"
DEVICE_MODEL = "EcoStream"



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
