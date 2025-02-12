"""Config flow for ecostream integration."""
from __future__ import annotations

import logging
from typing import Any, Optional
import voluptuous as vol # type: ignore

from homeassistant import config_entries # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.data_entry_flow import FlowResult # type: ignore
from homeassistant.const import CONF_HOST
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo # type: ignore

from .const import DOMAIN  # Import your domain name from const.py
from .__init__ import EcostreamWebsocketsAPI  # Import the API class

LOGGER = logging.getLogger(__name__)

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
            api = await self._test_connection(host)
            valid = api is not None

            if valid:
                # Create a config entry if the connection is valid
                return self.async_create_entry(title=self.api._device_name, data=user_input)
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle zeroconf discovery."""
        self.host = f"{discovery_info.host}:{discovery_info.port}"
        LOGGER.debug("Discovered device: %s", self.host)

        self.api = await self._test_connection(self.host)

        if self.api is None: 
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(self.api._device_name)

        self._abort_if_unique_id_configured(
            updates={CONF_HOST: self.host},
            error="already_configured_device",
        )

        self.context.update(
            {
                "title_placeholders": {
                    "name": self.api._device_name,
                },
            }
        )
            
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.api._device_name,
                data={CONF_HOST: self.host},
            )

        self._set_confirm_only()

        return self.async_show_form(step_id="discovery_confirm")

    async def _test_connection(self, host: str) -> Optional[EcostreamWebsocketsAPI]:
        """Test the WebSocket connection to the specified host."""
        try:
            api = EcostreamWebsocketsAPI()
            await api.connect(host)
            await api.get_data()  # Attempt to fetch data to confirm the connection works
            return api
        except Exception as e:
            LOGGER.error("Failed to connect to %s: %s", host, e)
            return None

    async def async_step_reauth(self, data: dict) -> FlowResult:
        """Handle re-authentication."""
        self.context["title_placeholders"] = {
            CONF_HOST: data[CONF_HOST],
        }
        return await self.async_step_user(user_input=data)
