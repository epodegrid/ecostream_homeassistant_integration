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
from unittest.mock import AsyncMock, MagicMock, patch

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
    # When host is None, we need to ensure discovery_info.host returns None
    # not "0.0.0.0", so we use a placeholder IP but set ip_addresses to empty
    if host:
        return ZeroconfServiceInfo(
            ip_address=ip_address(host),
            ip_addresses=[ip_address(host)],
            hostname=name,
            name=name,
            port=80,
            properties={},
            type="_http._tcp.local.",
        )
    else:
        # For None host, use minimal info that results in .host being None
        return ZeroconfServiceInfo(
            ip_address=ip_address(
                "127.0.0.1"
            ),  # Placeholder, won't be used
            ip_addresses=[],  # Empty list means no valid addresses
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
    # Use a mock to ensure .host is explicitly None
    from unittest.mock import MagicMock

    mock_discovery_info = MagicMock(spec=ZeroconfServiceInfo)
    mock_discovery_info.host = None
    mock_discovery_info.name = "ecostream"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=mock_discovery_info,
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


# ---------------------------------------------------------------------------
# _probe_ecostream error handling
# ---------------------------------------------------------------------------


async def test_probe_ecostream_non_text_message(
    hass: HomeAssistant,
) -> None:
    """Test probe handles non-TEXT WebSocket messages."""
    from aiohttp import WSMsgType
    import pytest

    from custom_components.ecostream.config_flow import (
        CannotConnect,
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    mock_ws = AsyncMock()
    mock_msg = AsyncMock()
    mock_msg.type = WSMsgType.BINARY
    mock_ws.receive = AsyncMock(return_value=mock_msg)
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.ws_connect = MagicMock(return_value=mock_ws)

    with patch(
        "custom_components.ecostream.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        with pytest.raises(CannotConnect):
            await flow._probe_ecostream("192.168.1.1")


async def test_probe_ecostream_json_decode_error(
    hass: HomeAssistant,
) -> None:
    """Test probe handles invalid JSON."""
    from aiohttp import WSMsgType
    import pytest

    from custom_components.ecostream.config_flow import (
        CannotConnect,
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    mock_ws = AsyncMock()
    mock_msg = AsyncMock()
    mock_msg.type = WSMsgType.TEXT
    mock_msg.data = "not valid json{"
    mock_ws.receive = AsyncMock(return_value=mock_msg)
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.ws_connect = MagicMock(return_value=mock_ws)

    with patch(
        "custom_components.ecostream.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        with pytest.raises(CannotConnect):
            await flow._probe_ecostream("192.168.1.1")


async def test_probe_ecostream_invalid_payload_type(
    hass: HomeAssistant,
) -> None:
    """Test probe handles non-dict payload."""
    from aiohttp import WSMsgType
    import pytest

    from custom_components.ecostream.config_flow import (
        CannotConnect,
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    mock_ws = AsyncMock()
    mock_msg = AsyncMock()
    mock_msg.type = WSMsgType.TEXT
    mock_msg.data = '["list", "not", "dict"]'
    mock_ws.receive = AsyncMock(return_value=mock_msg)
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.ws_connect = MagicMock(return_value=mock_ws)

    with patch(
        "custom_components.ecostream.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        with pytest.raises(CannotConnect):
            await flow._probe_ecostream("192.168.1.1")


async def test_probe_ecostream_timeout_error(
    hass: HomeAssistant,
) -> None:
    """Test probe handles timeout."""
    import pytest

    from custom_components.ecostream.config_flow import (
        CannotConnect,
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    mock_session = MagicMock()
    mock_session.ws_connect = MagicMock(side_effect=TimeoutError())

    with patch(
        "custom_components.ecostream.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        with pytest.raises(CannotConnect):
            await flow._probe_ecostream("192.168.1.1")


async def test_probe_ecostream_generic_exception(
    hass: HomeAssistant,
) -> None:
    """Test probe handles unexpected exceptions."""
    import pytest

    from custom_components.ecostream.config_flow import (
        CannotConnect,
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    mock_session = MagicMock()
    mock_session.ws_connect = MagicMock(
        side_effect=RuntimeError("Unexpected error")
    )

    with patch(
        "custom_components.ecostream.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        with pytest.raises(CannotConnect):
            await flow._probe_ecostream("192.168.1.1")


# ---------------------------------------------------------------------------
# _build_ws_url
# ---------------------------------------------------------------------------


async def test_build_ws_url_with_scheme(hass: HomeAssistant) -> None:
    """Test building WebSocket URL when scheme is already present."""
    from custom_components.ecostream.config_flow import (
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    url = flow._build_ws_url("http://192.168.1.1")
    assert url == "http://192.168.1.1/"

    url2 = flow._build_ws_url("https://192.168.1.1:8080")
    assert url2 == "https://192.168.1.1:8080/"


async def test_build_ws_url_without_scheme(
    hass: HomeAssistant,
) -> None:
    """Test building WebSocket URL without scheme."""
    from custom_components.ecostream.config_flow import (
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    url = flow._build_ws_url("192.168.1.1")
    assert url == "http://192.168.1.1/"


async def test_build_ws_url_strips_trailing_slash(
    hass: HomeAssistant,
) -> None:
    """Test building WebSocket URL strips trailing slashes."""
    from custom_components.ecostream.config_flow import (
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass

    url = flow._build_ws_url("192.168.1.1/")
    assert url == "http://192.168.1.1/"


# ---------------------------------------------------------------------------
# async_get_options_flow
# ---------------------------------------------------------------------------


async def test_async_get_options_flow(hass: HomeAssistant) -> None:
    """Test getting options flow."""
    from unittest.mock import MagicMock

    from custom_components.ecostream.config_flow import (
        EcostreamConfigFlow,
    )
    from custom_components.ecostream.options_flow import (
        EcostreamOptionsFlow,
    )

    entry = MagicMock()
    entry.options = {}

    flow = EcostreamConfigFlow.async_get_options_flow(entry)
    assert isinstance(flow, EcostreamOptionsFlow)


# ---------------------------------------------------------------------------
# Confirm step without host
# ---------------------------------------------------------------------------


async def test_confirm_step_without_host_aborts(
    hass: HomeAssistant,
) -> None:
    """Test confirm step aborts when host is not set."""
    from custom_components.ecostream.config_flow import (
        EcostreamConfigFlow,
    )

    flow = EcostreamConfigFlow()
    flow.hass = hass
    flow._host = None  # Simulate missing host

    result = await flow.async_step_confirm(user_input={})

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "unknown"
