from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResultType

sys.path.append(str(Path(__file__).resolve().parents[1]))

from custom_components.ecostream.const import DOMAIN
import custom_components.ecostream.config_flow as config_flow
import custom_components.ecostream.const as const


MOCK_HOST = "192.168.1.100"
MOCK_SYSTEM_NAME = "EcoStream-Test"


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
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    flow_id = result.get("flow_id")
    assert isinstance(flow_id, str)

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(
            flow_id, {CONF_HOST: MOCK_HOST}
        )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("title") == MOCK_SYSTEM_NAME
    assert result2.get("data") == {CONF_HOST: MOCK_HOST}


async def test_user_step_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    flow_id = result.get("flow_id")
    assert isinstance(flow_id, str)

    with _patch_probe(side_effect=config_flow.CannotConnect):
        result2 = await hass.config_entries.flow.async_configure(
            flow_id, {CONF_HOST: MOCK_HOST}
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}


async def test_user_step_unknown_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    flow_id = result.get("flow_id")
    assert isinstance(flow_id, str)

    with _patch_probe(side_effect=Exception("unexpected")):
        result2 = await hass.config_entries.flow.async_configure(
            flow_id, {CONF_HOST: MOCK_HOST}
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "unknown"}


async def test_user_step_already_configured(hass: HomeAssistant) -> None:
    with _patch_probe():
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        flow_id = result.get("flow_id")
        assert isinstance(flow_id, str)
        await hass.config_entries.flow.async_configure(
            flow_id, {CONF_HOST: MOCK_HOST}
        )

    result2 = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with _patch_probe():
        flow_id2 = result2.get("flow_id")
        assert isinstance(flow_id2, str)
        result3 = await hass.config_entries.flow.async_configure(
            flow_id2, {CONF_HOST: MOCK_HOST}
        )

    assert result3.get("type") == FlowResultType.ABORT
    assert result3.get("reason") == "already_configured"


# ---------------------------------------------------------------------------
# ZEROCONF STEP
# ---------------------------------------------------------------------------

async def test_zeroconf_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "confirm"
    flow_id = result.get("flow_id")
    assert isinstance(flow_id, str)

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(
            flow_id, {}
        )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("data") == {CONF_HOST: MOCK_HOST}


async def test_zeroconf_step_no_host_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": None, "name": "EcoStream"},
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "unknown"


async def test_zeroconf_step_already_configured(hass: HomeAssistant) -> None:
    with _patch_probe():
        r1 = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        flow_id = r1.get("flow_id")
        assert isinstance(flow_id, str)
        await hass.config_entries.flow.async_configure(
            flow_id, {CONF_HOST: MOCK_HOST}
        )

    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


# ---------------------------------------------------------------------------
# DHCP STEP
# ---------------------------------------------------------------------------

async def test_dhcp_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data={"ip": MOCK_HOST, "hostname": MOCK_SYSTEM_NAME},
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "confirm"
    flow_id = result.get("flow_id")
    assert isinstance(flow_id, str)

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(
            flow_id, {}
        )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("data") == {CONF_HOST: MOCK_HOST}


async def test_dhcp_step_no_ip_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data={"ip": None, "hostname": "ecostream"},
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "unknown"


async def test_dhcp_step_already_configured(hass: HomeAssistant) -> None:
    with _patch_probe():
        r1 = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        flow_id = r1.get("flow_id")
        assert isinstance(flow_id, str)
        await hass.config_entries.flow.async_configure(
            flow_id, {CONF_HOST: MOCK_HOST}
        )

    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data={"ip": MOCK_HOST, "hostname": MOCK_SYSTEM_NAME},
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


# ---------------------------------------------------------------------------
# CONFIRM STEP
# ---------------------------------------------------------------------------

async def test_confirm_step_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result.get("step_id") == "confirm"
    flow_id = result.get("flow_id")
    assert isinstance(flow_id, str)

    with _patch_probe(side_effect=config_flow.CannotConnect):
        result2 = await hass.config_entries.flow.async_configure(
            flow_id, {}
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}


async def test_confirm_step_unknown_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data={"host": MOCK_HOST, "name": f"{MOCK_SYSTEM_NAME}._http._tcp.local."},
    )
    assert result.get("step_id") == "confirm"
    flow_id = result.get("flow_id")
    assert isinstance(flow_id, str)

    with _patch_probe(side_effect=Exception("boom")):
        result2 = await hass.config_entries.flow.async_configure(
            flow_id, {}
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "unknown"}


# ---------------------------------------------------------------------------
# REAUTH STEP
# ---------------------------------------------------------------------------

async def test_reauth_step_redirects_to_user(hass: HomeAssistant) -> None:
    with _patch_probe():
        init = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        flow_id = init.get("flow_id")
        assert isinstance(flow_id, str)
        entry_result = await hass.config_entries.flow.async_configure(
            flow_id, {CONF_HOST: MOCK_HOST}
        )
    assert entry_result.get("type") == FlowResultType.CREATE_ENTRY
    config_entry = entry_result.get("result")
    assert config_entry is not None
    entry_id = config_entry.entry_id

    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry_id},
        data={CONF_HOST: MOCK_HOST},
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
