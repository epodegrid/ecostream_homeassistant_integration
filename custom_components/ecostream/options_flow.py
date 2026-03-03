from __future__ import annotations

import voluptuous as vol
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback

from .const import (
    CONF_PUSH_INTERVAL,
    CONF_FAST_PUSH_INTERVAL,
    DEFAULT_PUSH_INTERVAL,
    DEFAULT_FAST_PUSH_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class EcostreamOptionsFlow(config_entries.OptionsFlow):
    """Handle EcoStream configuration options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize EcoStream options flow."""
        self._entry = config_entry
        self._options = dict(config_entry.options)

    # --------------------------------------------------------------
    # STEP: Options menu
    # --------------------------------------------------------------
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:

        errors: dict[str, str] = {}

        if user_input is not None:
            # validate numeric values
            try:
                push_interval = float(user_input.get(CONF_PUSH_INTERVAL, 0))
                fast_push_interval = float(user_input.get(CONF_FAST_PUSH_INTERVAL, 0))

                if push_interval < 30:
                    errors["base"] = "push_interval_too_short"
                elif fast_push_interval < 5:
                    errors["base"] = "fast_interval_too_short"
                else:
                    # Update options
                    self._options[CONF_PUSH_INTERVAL] = push_interval
                    self._options[CONF_FAST_PUSH_INTERVAL] = fast_push_interval

                    return self.async_create_entry(
                        title="EcoStream Options",
                        data=self._options,
                    )

            except ValueError:
                errors["base"] = "invalid_number"

        # Defaults to existing or hard-coded defaults
        current_push = self._options.get(
            CONF_PUSH_INTERVAL, DEFAULT_PUSH_INTERVAL
        )
        current_fast = self._options.get(
            CONF_FAST_PUSH_INTERVAL, DEFAULT_FAST_PUSH_INTERVAL
        )

        schema = vol.Schema({
            vol.Required(
                CONF_PUSH_INTERVAL,
                default=current_push,
            ): vol.Coerce(float),
            vol.Required(
                CONF_FAST_PUSH_INTERVAL,
                default=current_fast,
            ): vol.Coerce(float),
        })

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
    ) -> "EcostreamOptionsFlow":
        return EcostreamOptionsFlow(config_entry)
