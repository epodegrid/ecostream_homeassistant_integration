from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ecostream.config_flow import CannotConnect
from custom_components.ecostream.const import DOMAIN

MOCK_HOST = "192.168.1.100"
MOCK_SYSTEM_NAME = "EcoStream-Test"
PROBE_OK = AsyncMock(return_value={"system_name": MOCK_SYSTEM_NAME})
PROBE_FAIL = AsyncMock(side_effect=CannotConnect)
PROBE_UNKNOWN = AsyncMock(side_effect=Exception("boom"))


def _patch_probe(return_value=None, side_effect=None):
    mock = AsyncMock()
    if side_effect:
        mock.side_effect = side_effect
    else:
        mock.return_value = return_value or {"system_name": MOCK_SYSTEM_NAME}
    return patch(
        "custom_components.ecostream.config_flow.EcostreamConfigFlow._probe_ecostream",
        mock,
    )


# ---------------------------------------------------------------------------
# USER STEP
# ---------------------------------------------------------------------------

async def test_user_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_SYSTEM_NAME
    assert result2["data"] == {CONF_HOST: MOCK_HOST}


async def test_user_step_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_probe(side_effect=CannotConnect):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_user_step_unknown_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_probe(side_effect=Exception("unexpected")):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_user_step_already_configured(hass: HomeAssistant) -> None:
    with _patch_probe():
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with _patch_probe():
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    assert result3["type"] == FlowResultType.ABORT
    assert result3["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# ZEROCONF STEP
# ---------------------------------------------------------------------------

async def test_zeroconf_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {CONF_HOST: MOCK_HOST}


async def test_zeroconf_step_no_host_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": None, "name": "EcoStream"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_zeroconf_step_already_configured(hass: HomeAssistant) -> None:
    with _patch_probe():
        r1 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            r1["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# DHCP STEP
# ---------------------------------------------------------------------------

async def test_dhcp_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data={"ip": MOCK_HOST, "hostname": MOCK_SYSTEM_NAME},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {CONF_HOST: MOCK_HOST}


async def test_dhcp_step_no_ip_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data={"ip": None, "hostname": "ecostream"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_dhcp_step_already_configured(hass: HomeAssistant) -> None:
    with _patch_probe():
        r1 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            r1["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data={"ip": MOCK_HOST, "hostname": MOCK_SYSTEM_NAME},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# CONFIRM STEP
# ---------------------------------------------------------------------------

async def test_confirm_step_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result["step_id"] == "confirm"

    with _patch_probe(side_effect=CannotConnect):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_confirm_step_unknown_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result["step_id"] == "confirm"

    with _patch_probe(side_effect=Exception("boom")):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


# ---------------------------------------------------------------------------
# REAUTH STEP
# ---------------------------------------------------------------------------

async def test_reauth_step_redirects_to_user(hass: HomeAssistant) -> None:
    with _patch_probe():
        init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        entry_result = await hass.config_entries.flow.async_configure(
            init["flow_id"], {CONF_HOST: MOCK_HOST}
        )
    assert entry_result["type"] == FlowResultType.CREATE_ENTRY
    entry_id = entry_result["result"].entry_id

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry_id},
        data={CONF_HOST: MOCK_HOST},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
