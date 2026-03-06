from __future__ import annotations

from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigFlowResult,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
import logging
from typing import Any

import voluptuous as vol

from .const import (
    CONF_FAST_PUSH_INTERVAL,
    CONF_FILTER_REPLACEMENT_DAYS,
    CONF_PRESET_HIGH_PCT,
    CONF_PRESET_LOW_PCT,
    CONF_PRESET_MID_PCT,
    CONF_PUSH_INTERVAL,
    DEFAULT_FAST_PUSH_INTERVAL,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
    DEFAULT_PRESET_HIGH_PCT,
    DEFAULT_PRESET_LOW_PCT,
    DEFAULT_PRESET_MID_PCT,
    DEFAULT_PUSH_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class EcostreamOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle EcoStream configuration options."""

    def __init__(
        self, config_entry: config_entries.ConfigEntry
    ) -> None:
        """Initialize EcoStream options flow."""
        super().__init__(config_entry)
        self._entry = config_entry
        self._options = dict(config_entry.options)

    # --------------------------------------------------------------
    # STEP: Options menu
    # --------------------------------------------------------------
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                push_interval = int(user_input[CONF_PUSH_INTERVAL])
                fast_push_interval = int(user_input[CONF_FAST_PUSH_INTERVAL])
                filter_days = int(user_input[CONF_FILTER_REPLACEMENT_DAYS])
                preset_low = int(user_input[CONF_PRESET_LOW_PCT])
                preset_mid = int(user_input[CONF_PRESET_MID_PCT])
                preset_high = int(user_input[CONF_PRESET_HIGH_PCT])

                if push_interval < 30:
                    errors["base"] = "push_interval_too_short"
                elif fast_push_interval < 5:
                    errors["base"] = "fast_interval_too_short"
                elif filter_days < 1:
                    errors["base"] = "invalid_number"
                elif not (0 < preset_low < preset_mid < preset_high <= 100):
                    errors["base"] = "invalid_preset_order"
                else:
                    self._options[CONF_PUSH_INTERVAL] = push_interval
                    self._options[CONF_FAST_PUSH_INTERVAL] = fast_push_interval
                    self._options[CONF_FILTER_REPLACEMENT_DAYS] = filter_days
                    self._options[CONF_PRESET_LOW_PCT] = preset_low
                    self._options[CONF_PRESET_MID_PCT] = preset_mid
                    self._options[CONF_PRESET_HIGH_PCT] = preset_high

                    return self.async_create_entry(
                        title="EcoStream Options",
                        data=self._options,
                    )

            except ValueError:
                errors["base"] = "invalid_number"

        current_push = self._options.get(CONF_PUSH_INTERVAL, DEFAULT_PUSH_INTERVAL)
        current_fast = self._options.get(CONF_FAST_PUSH_INTERVAL, DEFAULT_FAST_PUSH_INTERVAL)
        current_filter_days = self._options.get(CONF_FILTER_REPLACEMENT_DAYS, DEFAULT_FILTER_REPLACEMENT_DAYS)
        current_low = self._options.get(CONF_PRESET_LOW_PCT, DEFAULT_PRESET_LOW_PCT)
        current_mid = self._options.get(CONF_PRESET_MID_PCT, DEFAULT_PRESET_MID_PCT)
        current_high = self._options.get(CONF_PRESET_HIGH_PCT, DEFAULT_PRESET_HIGH_PCT)

        schema = vol.Schema(
            {
                vol.Required(CONF_PUSH_INTERVAL, default=current_push): int,
                vol.Required(CONF_FAST_PUSH_INTERVAL, default=current_fast): int,
                vol.Required(CONF_FILTER_REPLACEMENT_DAYS, default=current_filter_days): int,
                vol.Required(CONF_PRESET_LOW_PCT, default=current_low): vol.All(int, vol.Range(min=1, max=99)),
                vol.Required(CONF_PRESET_MID_PCT, default=current_mid): vol.All(int, vol.Range(min=1, max=99)),
                vol.Required(CONF_PRESET_HIGH_PCT, default=current_high): vol.All(int, vol.Range(min=1, max=100)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "host": self._entry.data.get(CONF_HOST, "EcoStream"),
            },
        )

    # --------------------------------------------------------------
    # Required by HA 2025+
    # --------------------------------------------------------------
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EcostreamOptionsFlow:
        return EcostreamOptionsFlow(config_entry)
