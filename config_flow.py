"""Config flow for ecostream integration."""
from __future__ import annotations

import logging
import voluptuous as vol # type: ignore

from homeassistant import config_entries # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.data_entry_flow import FlowResult # type: ignore
from homeassistant.const import CONF_HOST # type: ignore

from .const import DOMAIN  # Import your domain name from const.py
from .__init__ import EcostreamWebsocketsAPI  # Import the API class

_LOGGER = logging.getLogger(__name__)

# Define the configuration schema
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
})

class EcostreamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ecostream."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            # Validate the WebSocket connection
            valid = await self._test_connection(host)
            if valid:
                # Create a config entry if the connection is valid
                return self.async_create_entry(title="Ecostream", data=user_input)
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _test_connection(self, host: str) -> bool:
        """Test the WebSocket connection to the specified host."""
        try:
            api = EcostreamWebsocketsAPI()
            await api.connect(host)
            await api.get_data()  # Attempt to fetch data to confirm the connection works
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to %s: %s", host, e)
            return False

    async def async_step_import(self, import_data=None) -> FlowResult:
        """Handle the import step (for configuration.yaml entries)."""
        if import_data:
            return await self.async_step_user(user_input=import_data)
        return self.async_abort(reason="not_supported")

    async def async_step_reauth(self, data: dict) -> FlowResult:
        """Handle re-authentication."""
        self.context["title_placeholders"] = {
            CONF_HOST: data[CONF_HOST],
        }
        return await self.async_step_user(user_input=data)
