from __future__ import annotations

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import (
    ZeroconfServiceInfo,
)
import json
import logging
from typing import Any

from aiohttp import ClientError, WSMsgType
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


# ---------------------------------------------------------------------------
# Config Flow
# ---------------------------------------------------------------------------


class EcostreamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handles the EcoStream configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the EcoStream config flow."""
        self._host: str | None = None
        self._discovered_name: str | None = None

    # ======================================================================
    # USER STEP
    # ======================================================================
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            self._host = host

            try:
                info = await self._probe_ecostream(host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception(
                    "Unexpected error during EcoStream validation"
                )
                errors["base"] = "unknown"
            else:
                system_name = (
                    info.get("system_name") or f"EcoStream ({host})"
                )

                await self.async_set_unique_id(system_name)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host}
                )

                return self.async_create_entry(
                    title=system_name,
                    data={CONF_HOST: host},
                )

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._host or ""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=data_schema,
        )

    # ======================================================================
    # ZEROCONF STEP
    # ======================================================================
    async def async_step_zeroconf(
        self,
        discovery_info: ZeroconfServiceInfo,
    ) -> ConfigFlowResult:

        host = discovery_info.host
        name = discovery_info.name or "EcoStream"

        if not host or host in ("0.0.0.0", "::"):
            return self.async_abort(reason="unknown")

        system_name = name.split(".")[0]

        _LOGGER.info(
            "EcoStream discovered via Zeroconf: host=%s, name=%s",
            host,
            name,
        )

        self._host = host
        self._discovered_name = system_name

        await self.async_set_unique_id(system_name)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        return await self.async_step_confirm()

    # ======================================================================
    # DHCP STEP
    # ======================================================================
    async def async_step_dhcp(
        self,
        discovery_info: DhcpServiceInfo,
    ) -> ConfigFlowResult:

        host = discovery_info.ip
        hostname = getattr(discovery_info, "hostname", "EcoStream")

        if not host:
            return self.async_abort(reason="unknown")

        system_name = hostname.split(".")[0]

        _LOGGER.info(
            "EcoStream discovered via DHCP: host=%s hostname=%s",
            host,
            hostname,
        )

        self._host = host
        self._discovered_name = system_name

        await self.async_set_unique_id(system_name)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        return await self.async_step_confirm()

    # ======================================================================
    # CONFIRMATION
    # ======================================================================
    async def async_step_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:

        errors: dict[str, str] = {}

        if user_input is not None:
            if not self._host:
                errors["base"] = "cannot_connect"
            else:
                try:
                    info = await self._probe_ecostream(self._host)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception(
                        "Unexpected error while validating EcoStream"
                    )
                    errors["base"] = "unknown"
                else:
                    system_name = (
                        info.get("system_name")
                        or self._discovered_name
                        or f"EcoStream ({self._host})"
                    )

                    await self.async_set_unique_id(system_name)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: self._host}
                    )

                    return self.async_create_entry(
                        title=system_name,
                        data={CONF_HOST: self._host},
                    )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),  # Only OK button
            errors=errors,
            description_placeholders={
                "host": self._host or "",
                "name": self._discovered_name or "EcoStream",
            },
        )

    # ======================================================================
    # REAUTH STEP
    # ======================================================================
    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        self._host = entry_data.get(CONF_HOST)
        return await self.async_step_user()

    # ======================================================================
    # HELPER: Probe device
    # ======================================================================
    async def _probe_ecostream(self, host: str) -> dict[str, Any]:
        """Open a temporary WebSocket and read one message."""
        session = async_get_clientsession(self.hass)
        url = self._build_ws_url(host)

        _LOGGER.debug("Probing EcoStream via %s", url)

        try:
            async with session.ws_connect(url, heartbeat=None) as ws:
                msg = await ws.receive(timeout=5)

                if msg.type != WSMsgType.TEXT:
                    raise CannotConnect("Unexpected WS message type")

                try:
                    payload = json.loads(msg.data)
                except json.JSONDecodeError as err:
                    raise CannotConnect("Invalid JSON") from err

                if not isinstance(payload, dict):
                    raise CannotConnect("Invalid payload")

                system = payload.get("system", {})
                system_name = system.get("system_name")

                return {"system_name": system_name}

        except (TimeoutError, ClientError) as err:
            raise CannotConnect from err
        except CannotConnect:
            raise
        except Exception as err:
            _LOGGER.exception("Probe error: %s", err)
            raise CannotConnect from err

    def _build_ws_url(self, host: str) -> str:
        """Always connect to / over HTTP."""
        host = host.strip().rstrip("/")
        if "://" in host:
            return f"{host}/"
        return f"http://{host}/"

    # ======================================================================
    # OPTIONS FLOW
    # ======================================================================
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import EcostreamOptionsFlow

        return EcostreamOptionsFlow(config_entry)
