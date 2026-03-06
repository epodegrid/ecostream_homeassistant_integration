from __future__ import annotations

import asyncio
from collections.abc import Mapping
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)
import logging
import random
import time
from typing import Any

from .const import (
    CONF_FAST_PUSH_INTERVAL,
    CONF_PUSH_INTERVAL,
    DEFAULT_FAST_PUSH_INTERVAL,
    DEFAULT_PUSH_INTERVAL,
    DOMAIN,
    FAST_KEYS,
    FAST_MODE_SECONDS,
    SLOW_KEYS,
)
from .websocket_api import EcostreamWebsocket

_LOGGER = logging.getLogger(__name__)

RECONNECT_INTERVAL = 3600
RECONNECT_JITTER = 300
RECONNECT_MIN_SLEEP = 60


class EcostreamDataUpdateCoordinator(
    DataUpdateCoordinator[Mapping[str, Any]]
):
    """Manages EcoStream WebSocket data & push scheduling (pure push model)."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        options: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize the EcoStream coordinator.

        Args:
            hass: The Home Assistant instance.
            host: The EcoStream device host address.
            options: Optional configuration options for push intervals.
        """
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="BUVA EcoStream",
            update_interval=None,
        )

        self.host = host
        self.options = dict(options or {})

        self._push_interval: float = float(
            self.options.get(CONF_PUSH_INTERVAL, DEFAULT_PUSH_INTERVAL)
        )
        self._fast_push_interval: float = float(
            self.options.get(
                CONF_FAST_PUSH_INTERVAL, DEFAULT_FAST_PUSH_INTERVAL
            )
        )

        self._last_push: float = 0.0
        self._last_slow_push: float = 0.0
        self._fast_mode_until: float = 0.0

        self._last_slow_snapshot: dict[str, Any] = {}
        self.data: Mapping[str, Any] = {}

        self.ws: EcostreamWebsocket | None = None

        self._reconnect_task: asyncio.Task[None] | None = None
        self._started: bool = False
        self._stopping: bool = False

        self.boost_duration_minutes: int = 0
        self.boost_remaining_seconds: int = 0

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def async_start(self) -> None:
        """Start websocket + register background tasks."""
        if self._started:
            return

        self._started = True
        self._stopping = False

        await self._ensure_ws_started()

        # Ensure background tasks only start once HA is fully running
        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            self._async_start_background_tasks,
        )

        # Ensure clean shutdown
        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP,
            self._async_handle_hass_stop,
        )

    async def async_stop(self) -> None:
        """Stop everything cleanly."""
        self._stopping = True

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        if self.ws:
            await self.ws.async_disconnect()
            self.ws = None

    async def _async_handle_hass_stop(self, event: Event) -> None:
        """Handle HA shutdown."""
        await self.async_stop()

    # ==========================================================
    # Background Tasks (SAFE)
    # ==========================================================

    async def _async_start_background_tasks(self, event: Event) -> None:
        """Start reconnect loop safely inside HA event loop."""
        if self._reconnect_task:
            return

        _LOGGER.debug("Starting EcoStream reconnect loop")

        self._reconnect_task = asyncio.create_task(
            self._async_reconnect_loop(),
            name="ecostream_ws_hourly_reconnect",
        )

    async def _async_reconnect_loop(self) -> None:
        """Reconnect hourly with jitter."""
        try:
            while not self._stopping:
                jitter = random.uniform(
                    -RECONNECT_JITTER, RECONNECT_JITTER
                )
                sleep_s = max(
                    RECONNECT_MIN_SLEEP, RECONNECT_INTERVAL + jitter
                )

                await asyncio.sleep(sleep_s)

                if self._stopping:
                    return

                _LOGGER.debug(
                    "Scheduled EcoStream reconnect (sleep=%.0fs)",
                    sleep_s,
                )

                await self._force_ws_reconnect()

        except asyncio.CancelledError:
            _LOGGER.debug("Reconnect loop cancelled")
            raise
        except Exception:
            _LOGGER.exception("Reconnect loop crashed")

    # ==========================================================
    # WebSocket Handling
    # ==========================================================

    async def _ensure_ws_started(self) -> None:
        """Ensure websocket exists and is running."""
        if self.ws is None:
            self.ws = EcostreamWebsocket(
                hass=self.hass,
                host=self.host,
                message_callback=self.handle_ws_message,
            )

        await self.ws.async_start()
        _LOGGER.info("EcoStream WebSocket started for %s", self.host)

    async def _force_ws_reconnect(self) -> None:
        """Force clean reconnect."""
        if self.ws is None:
            await self._ensure_ws_started()
            return

        _LOGGER.info("Forcing EcoStream reconnect for %s", self.host)

        await self.ws.async_disconnect()
        await self.ws.async_start()

        self._last_push = 0.0

    # ==========================================================
    # Fast Mode
    # ==========================================================

    def mark_control_action(self) -> None:
        self._fast_mode_until = time.time() + FAST_MODE_SECONDS

    # ==========================================================
    # Message Handling
    # ==========================================================

    async def handle_ws_message(self, message: dict[str, Any]) -> None:
        self._merge_payload(message)

        now = time.time()

        has_fast = any(k in message for k in FAST_KEYS)
        has_slow = any(k in message for k in SLOW_KEYS)

        in_fast = now < self._fast_mode_until
        interval = (
            self._fast_push_interval if in_fast else self._push_interval
        )

        should_push = False

        if self._last_push == 0:
            should_push = True
        elif has_fast and (now - self._last_push >= interval):
            should_push = True
        elif has_slow and (
            now - self._last_slow_push >= RECONNECT_INTERVAL
        ):
            should_push = True

        if not should_push:
            return

        self._last_push = now

        if has_slow:
            self._last_slow_push = now
            self._last_slow_snapshot = {
                k: self.data.get(k) for k in SLOW_KEYS if k in self.data
            }

        self.async_set_updated_data(dict(self.data))
        self._update_filter_issue()

    def _update_filter_issue(self) -> None:
        config = self.data.get("config", {})
        filter_warning = bool(config.get("filter_datetime", 0))
        if filter_warning:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "filter_replacement_overdue",
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="filter_replacement_overdue",
            )
        else:
            ir.async_delete_issue(
                self.hass, DOMAIN, "filter_replacement_overdue"
            )

    # ==========================================================
    # Fallback
    # ==========================================================

    async def _async_update_data(self) -> Mapping[str, Any]:
        return dict(self.data)

    # ==========================================================
    # Merge helper
    # ==========================================================

    def _merge_payload(self, incoming: dict[str, Any]) -> None:
        base = dict(self.data)
        for key, value in incoming.items():
            if isinstance(base.get(key), dict) and isinstance(
                value, dict
            ):
                base[key] = {**base[key], **value}
            else:
                base[key] = value
        self.data = base
