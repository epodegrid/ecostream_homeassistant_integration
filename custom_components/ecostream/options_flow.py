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
    CONF_BOOST_DURATION,
    CONF_FILTER_REPLACEMENT_DAYS,
    CONF_PRESET_OVERRIDE_MINUTES,
    DEFAULT_BOOST_DURATION_MINUTES,
    DEFAULT_FILTER_REPLACEMENT_DAYS,
    DEFAULT_PRESET_OVERRIDE_MINUTES,
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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                boost_duration = int(
                    user_input.get(
                        "boost_duration", DEFAULT_BOOST_DURATION_MINUTES
                    )
                )
                filter_days = int(
                    user_input[CONF_FILTER_REPLACEMENT_DAYS]
                )
                preset_override_minutes = int(
                    user_input[CONF_PRESET_OVERRIDE_MINUTES]
                )

                if boost_duration < 5:
                    errors["base"] = "invalid_number"
                elif filter_days < 30:
                    errors["base"] = "invalid_number"
                elif preset_override_minutes < 5:
                    errors["base"] = "invalid_number"
                else:
                    self._options[CONF_FILTER_REPLACEMENT_DAYS] = (
                        filter_days
                    )
                    self._options[CONF_PRESET_OVERRIDE_MINUTES] = (
                        preset_override_minutes
                    )
                    self._options[CONF_BOOST_DURATION] = boost_duration

                    return self.async_create_entry(
                        title="EcoStream Options",
                        data=self._options,
                    )

            except ValueError:
                errors["base"] = "invalid_number"

        current_filter_days = self._options.get(
            CONF_FILTER_REPLACEMENT_DAYS,
            DEFAULT_FILTER_REPLACEMENT_DAYS,
        )
        current_override_minutes = self._options.get(
            CONF_PRESET_OVERRIDE_MINUTES,
            DEFAULT_PRESET_OVERRIDE_MINUTES,
        )
        current_boost_duration = self._options.get(
            CONF_BOOST_DURATION,
            DEFAULT_BOOST_DURATION_MINUTES,
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_FILTER_REPLACEMENT_DAYS,
                    default=current_filter_days,
                ): int,
                vol.Required(
                    CONF_PRESET_OVERRIDE_MINUTES,
                    default=current_override_minutes,
                ): vol.All(int, vol.Range(min=5)),
                vol.Required(
                    CONF_BOOST_DURATION,
                    default=current_boost_duration,
                ): vol.All(int, vol.Range(min=5)),
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
