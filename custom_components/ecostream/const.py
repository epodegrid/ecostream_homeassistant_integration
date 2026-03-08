from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecostream"

PLATFORMS: list[str] = [
    "button",
    "sensor",
    "fan",
    "select",
    "switch",
]

### THE BOOST AND DEFAULT OPTIONS BELOW ARE THE ONLY ONES YOU SHOULD NEED TO EDIT ###

# Boost
CO2_THRESHOLD = 800
BOOST_OPTIONS = ["5", "10", "15", "30", "60"]

# Default options
DEFAULT_FILTER_REPLACEMENT_DAYS = 180
DEFAULT_PRESET_OVERRIDE_MINUTES = 60
DEFAULT_BOOST_DURATION_MINUTES = 15
DEFAULT_SUMMER_COMFORT_TEMP = 22

### NO NEED TO EDIT BELOW THIS LINE UNLESS YOU KNOW WHAT YOU'RE DOING ###

# Config options
CONF_FILTER_REPLACEMENT_DAYS = "filter_replacement_days"
CONF_PRESET_OVERRIDE_MINUTES = "preset_override_minutes"
CONF_BOOST_DURATION = "boost_duration"
CONF_ALLOW_OVERRIDE_FILTER_DATE = "allow_override_filter_date"
CONF_SUMMER_COMFORT_TEMP = "summer_comfort_temp"

# Default push intervals (seconds)
FAST_MODE_SECONDS = 20
SLOW_PUSH_INTERVAL = 10

# Fan presets
PRESET_LOW = "low"
PRESET_MID = "mid"
PRESET_HIGH = "high"
PRESET_MODES = [PRESET_LOW, PRESET_MID, PRESET_HIGH]

# WebSocket timing
WS_HEARTBEAT_INTERVAL = 10
WS_STALE_TIMEOUT = 30
WS_RECONNECT_INITIAL_DELAY = 10
WS_RECONNECT_MAX_DELAY = 60

# Device info
DEVICE_NAME = "EcoStream"
DEVICE_MODEL = "EcoStream"

# ---------------------------------------------------------
# Push key groups
# ---------------------------------------------------------

FAST_KEYS = {
    "status",
    "ext_module",
}

SLOW_KEYS = {
    "config",
    "system",
    "comm_wifi",
    "comm_bt",
    "error",
    "debug",
}
