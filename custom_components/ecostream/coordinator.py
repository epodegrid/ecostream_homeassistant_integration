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
from typing import Any, cast

from .const import (
    DOMAIN,
    FAST_KEYS,
    FAST_MODE_SECONDS,
    SLOW_KEYS,
    SLOW_PUSH_INTERVAL,
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

        self._push_interval: float = float(SLOW_PUSH_INTERVAL)
        self._fast_push_interval: int = int(FAST_MODE_SECONDS)

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
        self._last_override_active: bool = False
        self._restore_schedule_after_override: bool = False

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

    async def async_send_config(
        self, cfg: dict[str, Any], action: str
    ) -> bool:
        if not self.ws:
            _LOGGER.error(
                "EcoStream WebSocket not connected, cannot send %s command",
                action,
            )
            return False

        self.mark_control_action()
        await self.ws.send_json({"config": cfg})

        override_seconds = self._parse_override_seconds(
            cfg.get("man_override_set_time")
        )
        if override_seconds is not None:
            if override_seconds > 0:
                self._last_override_active = True
                self._restore_schedule_after_override = (
                    action.startswith("preset")
                )
            else:
                self._last_override_active = False
                self._restore_schedule_after_override = False

        return True

    @staticmethod
    def _parse_override_seconds(value: Any) -> int | None:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _config_payload(self) -> dict[str, Any]:
        config = self.data.get("config")
        if isinstance(config, dict):
            return cast(dict[str, Any], config)
        return {}

    def _status_payload(self) -> dict[str, Any]:
        status = self.data.get("status")
        if isinstance(status, dict):
            return cast(dict[str, Any], status)
        return {}

    async def _maybe_restore_schedule_after_override(self) -> None:
        if not self._restore_schedule_after_override:
            return

        config = self._config_payload()
        if bool(config.get("schedule_enabled", False)):
            self._restore_schedule_after_override = False
            return

        # Check if a schedule actually exists before enabling it
        if not self._has_valid_schedule(config):
            _LOGGER.warning(
                "Preset override expired, but no schedule configured. "
                "EcoStream will remain in last state. Configure a schedule "
                "or manually adjust ventilation."
            )
            self._restore_schedule_after_override = False
            return

        ok = await self.async_send_config(
            {"schedule_enabled": True},
            "schedule restore after preset",
        )
        if ok:
            _LOGGER.debug(
                "Preset override expired; re-enabled schedule"
            )
            self._restore_schedule_after_override = False

    def _has_valid_schedule(self, config: dict[str, Any]) -> bool:
        """Check if EcoStream has a valid schedule configuration.

        The EcoStream stores schedule in various fields like schedule_0_time,
        schedule_0_value, etc. If none exist, there's no schedule to enable.
        """
        # Check for any schedule_X_time or schedule_X_value fields
        schedule_keys = [
            k
            for k in config.keys()
            if k.startswith("schedule_")
            and ("_time" in k or "_value" in k)
        ]

        if not schedule_keys:
            return False

        # Verify at least one schedule entry has both time and value
        for i in range(10):  # Most likely max 7-10 schedule items
            time_key = f"schedule_{i}_time"
            value_key = f"schedule_{i}_value"
            if time_key in config and value_key in config:
                # At least one valid schedule entry exists
                return True

        return False

    # ==========================================================
    # Message Handling
    # ==========================================================

    async def handle_ws_message(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        self._merge_payload(cast(dict[str, Any], message))

        status = self._status_payload()
        override_seconds = self._parse_override_seconds(
            status.get("override_set_time_left")
        )
        override_active = (
            override_seconds is not None and override_seconds > 0
        )
        if self._last_override_active and not override_active:
            await self._maybe_restore_schedule_after_override()
        self._last_override_active = override_active

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
            now - self._last_slow_push >= self._push_interval
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
        import time

        config = self.data.get("config", {})
        filter_ts = config.get("filter_datetime")
        filter_warning = (
            isinstance(filter_ts, (int, float))
            and filter_ts > 0
            and time.time() >= float(filter_ts)
        )
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
