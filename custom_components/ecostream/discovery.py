from __future__ import annotations

from homeassistant.config_entries import SOURCE_DHCP, SOURCE_ZEROCONF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import (
    ZeroconfServiceInfo,
)
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_process_zeroconf(
    hass: HomeAssistant,
    discovery_info: ZeroconfServiceInfo,
):
    """Handle EcoStream Zeroconf discovery."""

    name = discovery_info.name or ""
    if not name.startswith("EcoStream"):
        return

    ip = discovery_info.ip_address
    if not ip:
        return

    _LOGGER.info(
        "EcoStream discovered via Zeroconf: %s at %s",
        name,
        ip,
    )

    # Check if already configured
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("host") == str(ip):
            _LOGGER.debug(
                "EcoStream already configured for host %s", ip
            )
            return

    # Start config flow
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data={"host": str(ip)},
        )
    )


async def async_process_dhcp(
    hass: HomeAssistant,
    discovery_info: DhcpServiceInfo,
):
    """Handle EcoStream DHCP discovery."""

    hostname = (discovery_info.hostname or "").lower()
    if not hostname.startswith("ecostream"):
        return

    ip = discovery_info.ip
    if not ip:
        return

    _LOGGER.info(
        "EcoStream discovered via DHCP: hostname=%s ip=%s",
        hostname,
        ip,
    )

    # Avoid duplicates
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("host") == str(ip):
            _LOGGER.debug(
                "EcoStream already configured for host %s", ip
            )
            return

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_DHCP},
            data={"host": str(ip)},
        )
    )
