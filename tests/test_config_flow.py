from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import (
    ZeroconfServiceInfo,
)
from ipaddress import ip_address
from typing import Any, cast
from unittest.mock import AsyncMock, patch

from custom_components.ecostream.config_flow import CannotConnect
from custom_components.ecostream.const import DOMAIN

MOCK_HOST = "192.168.1.100"
MOCK_SYSTEM_NAME = "ecostream-test"
PROBE_OK = AsyncMock(return_value={"system_name": MOCK_SYSTEM_NAME})
PROBE_FAIL = AsyncMock(side_effect=CannotConnect)
PROBE_UNKNOWN = AsyncMock(side_effect=Exception("boom"))


def _config_input(data: dict[str, Any]) -> dict[str, Any]:
    """Cast config input to a typed dict for type checkers."""
    return data


def _patch_probe(
    return_value: dict[str, Any] | None = None,
    side_effect: type[Exception] | Exception | None = None,
):
    mock = AsyncMock()
    if side_effect:
        mock.side_effect = side_effect
    else:
        mock.return_value = return_value or {
            "system_name": MOCK_SYSTEM_NAME
        }
    return patch(
        "custom_components.ecostream.config_flow.EcostreamConfigFlow._probe_ecostream",
        mock,
    )


def _make_zeroconf_service_info(
    host: str | None, name: str
) -> ZeroconfServiceInfo:
    """Create a mock ZeroconfServiceInfo object."""
    return ZeroconfServiceInfo(
        ip_address=ip_address(host) if host else ip_address("0.0.0.0"),
        ip_addresses=[ip_address(host)] if host else [],
        hostname=name,
        name=name,
        port=80,
        properties={},
        type="_http._tcp.local.",
    )


def _make_dhcp_service_info(
    ip: str | None, hostname: str
) -> DhcpServiceInfo:
    """Create a mock DhcpServiceInfo object."""
    return DhcpServiceInfo(
        ip=ip or "",
        hostname=hostname,
        macaddress="f0ad4e000000",
    )


# ---------------------------------------------------------------------------
# USER STEP
# ---------------------------------------------------------------------------


async def test_user_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], _config_input({CONF_HOST: MOCK_HOST})
        )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("title") == MOCK_SYSTEM_NAME
    assert result2.get("data") == {CONF_HOST: MOCK_HOST}


async def test_user_step_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_probe(side_effect=CannotConnect):
        result2: config_entries.ConfigFlowResult = await cast(  # type: ignore[misc]
            Any, hass.config_entries.flow
        ).async_configure(
            result["flow_id"], _config_input({CONF_HOST: MOCK_HOST})
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}


async def test_user_step_unknown_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_probe(side_effect=Exception("unexpected")):
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], _config_input({CONF_HOST: MOCK_HOST})
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "unknown"}


async def test_user_step_already_configured(
    hass: HomeAssistant,
) -> None:
    with _patch_probe():
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], _config_input({CONF_HOST: MOCK_HOST})
        )

    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with _patch_probe():
        result3 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result2["flow_id"], _config_input({CONF_HOST: MOCK_HOST})
        )

    assert result3.get("type") == FlowResultType.ABORT
    assert result3.get("reason") == "already_configured"


# ---------------------------------------------------------------------------
# ZEROCONF STEP
# ---------------------------------------------------------------------------


async def test_zeroconf_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_service_info(
            host=MOCK_HOST,
            name=f"{MOCK_SYSTEM_NAME}._http._tcp.local.",
        ),
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "confirm"

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], _config_input({})
        )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("data") == {CONF_HOST: MOCK_HOST}


async def test_zeroconf_step_no_host_aborts(
    hass: HomeAssistant,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_service_info(host=None, name="ecostream"),
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "unknown"


async def test_zeroconf_step_already_configured(
    hass: HomeAssistant,
) -> None:
    with _patch_probe():
        r1 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            r1["flow_id"], _config_input({CONF_HOST: MOCK_HOST})
        )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_service_info(
            host=MOCK_HOST,
            name=f"{MOCK_SYSTEM_NAME}._http._tcp.local.",
        ),
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


# ---------------------------------------------------------------------------
# DHCP STEP
# ---------------------------------------------------------------------------


async def test_dhcp_step_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=_make_dhcp_service_info(
            ip=MOCK_HOST, hostname=MOCK_SYSTEM_NAME
        ),
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "confirm"

    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], {}
        )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("data") == {CONF_HOST: MOCK_HOST}


async def test_dhcp_step_no_ip_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=_make_dhcp_service_info(ip=None, hostname="ecostream"),
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "unknown"


async def test_dhcp_step_already_configured(
    hass: HomeAssistant,
) -> None:
    with _patch_probe():
        r1 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            r1["flow_id"], {CONF_HOST: MOCK_HOST}
        )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=_make_dhcp_service_info(
            ip=MOCK_HOST, hostname=MOCK_SYSTEM_NAME
        ),
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


# ---------------------------------------------------------------------------
# CONFIRM STEP
# ---------------------------------------------------------------------------


async def test_confirm_step_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_service_info(
            host=MOCK_HOST,
            name=f"{MOCK_SYSTEM_NAME}._http._tcp.local.",
        ),
    )
    assert result.get("step_id") == "confirm"

    with _patch_probe(side_effect=CannotConnect):
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], _config_input({})
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}


async def test_confirm_step_unknown_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_service_info(
            host=MOCK_HOST,
            name=f"{MOCK_SYSTEM_NAME}._http._tcp.local.",
        ),
    )
    assert result.get("step_id") == "confirm"

    with _patch_probe(side_effect=Exception("boom")):
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], _config_input({})
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "unknown"}


# ---------------------------------------------------------------------------
# REAUTH STEP
# ---------------------------------------------------------------------------


async def test_reauth_step_redirects_to_user(
    hass: HomeAssistant,
) -> None:
    with _patch_probe():
        init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        entry_result = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            init["flow_id"], _config_input({CONF_HOST: MOCK_HOST})
        )
    assert entry_result.get("type") == FlowResultType.CREATE_ENTRY
    entry_id = entry_result.get("result").entry_id  # type: ignore[union-attr]

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry_id,
        },
        data={CONF_HOST: MOCK_HOST},
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


# ---------------------------------------------------------------------------
# RECONFIGURE STEP
# ---------------------------------------------------------------------------


async def test_reconfigure_step_success(hass: HomeAssistant) -> None:
    """Test reconfigure flow with successful connection."""
    # First create an entry
    with _patch_probe():
        init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        entry_result = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            init["flow_id"], {CONF_HOST: MOCK_HOST}
        )
    assert entry_result.get("type") == FlowResultType.CREATE_ENTRY
    entry = entry_result.get("result")  # type: ignore[assignment]
    assert entry is not None

    # Start reconfigure flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"

    # Submit new host
    new_host = "192.168.1.200"
    with _patch_probe():
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"], _config_input({CONF_HOST: new_host})
        )

    assert result2.get("type") == FlowResultType.ABORT
    assert result2.get("reason") == "reconfigure_successful"


async def test_reconfigure_step_cannot_connect(
    hass: HomeAssistant,
) -> None:
    """Test reconfigure flow with connection error."""
    # First create an entry
    with _patch_probe():
        init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        entry_result = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            init["flow_id"], {CONF_HOST: MOCK_HOST}
        )
    entry = entry_result.get("result")  # type: ignore[assignment]
    assert entry is not None

    # Start reconfigure flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    # Submit new host that fails to connect
    with _patch_probe(side_effect=CannotConnect):
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"],
            _config_input({CONF_HOST: "192.168.1.200"}),
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}


async def test_reconfigure_step_unknown_error(
    hass: HomeAssistant,
) -> None:
    """Test reconfigure flow with unknown error."""
    # First create an entry
    with _patch_probe():
        init = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        entry_result = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            init["flow_id"], {CONF_HOST: MOCK_HOST}
        )
    entry = entry_result.get("result")  # type: ignore[assignment]
    assert entry is not None

    # Start reconfigure flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    # Submit new host with unexpected error
    with _patch_probe(side_effect=Exception("boom")):
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"],
            _config_input({CONF_HOST: "192.168.1.200"}),
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "unknown"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_probe(side_effect=CannotConnect):
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"],
            _config_input(
                {
                    CONF_HOST: "1.1.1.1",
                }
            ),
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_probe(side_effect=Exception("Invalid auth")):
        result2 = await hass.config_entries.flow.async_configure(  # type: ignore[misc]
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )

    assert result2.get("type") == FlowResultType.FORM
    assert result2.get("errors") == {"base": "unknown"}
