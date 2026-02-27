from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from aiohttp import ClientError, WSMsgType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    WS_HEARTBEAT_INTERVAL,
    WS_STALE_TIMEOUT,
    WS_RECONNECT_INITIAL_DELAY,
    WS_RECONNECT_MAX_DELAY,
)

_LOGGER = logging.getLogger(__name__)

MessageCallback = Callable[[dict[str, Any]], Awaitable[None]]


class EcostreamWebsocket:
    """Persistent, cancel-safe WebSocket client for the BUVA EcoStream."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        message_callback: MessageCallback,
    ) -> None:
        self._hass = hass
        host = (host or "").strip().strip("/")
        self._host = host
        self._ws_url = f"ws://{self._host}/"

        self._session = async_get_clientsession(hass)
        self._message_callback = message_callback

        self._task: Optional[asyncio.Task] = None
        self._ws = None
        self._stopping = False

        self._last_message_ts: float | None = None
        self._has_received_payload = False
        self._stale_logged = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        """Start the background WebSocket worker."""
        if self._task and not self._task.done():
            return

        self._stopping = False
        self._task = self._hass.loop.create_task(
            self._run(),
            name="ecostream_ws_loop",
        )

    async def async_disconnect(self) -> None:
        """Stop WebSocket loop quickly and cleanly."""
        self._stopping = True

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Error closing EcoStream WS", exc_info=True)

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        _LOGGER.info("EcoStream WebSocket loop stopped for %s", self._host)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_json(self, payload: dict[str, Any]) -> None:
        """Send JSON to the EcoStream device."""
        if not self._ws:
            _LOGGER.warning(
                "Cannot send JSON to EcoStream; WebSocket not connected (%s)",
                self._host,
            )
            return

        try:
            await self._ws.send_json(payload)
            _LOGGER.debug("Sent JSON to EcoStream %s: %s", self._host, payload)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to send JSON to EcoStream %s: %s", self._host, err)

    # ------------------------------------------------------------------
    # Main worker
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Persistent WS loop with instant shutdown and safe timeouts."""
        backoff = WS_RECONNECT_INITIAL_DELAY

        while not self._stopping:
            try:
                _LOGGER.info("Connecting to EcoStream WS at %s", self._ws_url)

                async with self._session.ws_connect(
                    self._ws_url,
                    heartbeat=None,  # we manage heartbeats manually
                ) as ws:
                    self._ws = ws
                    self._last_message_ts = time.time()
                    self._has_received_payload = False
                    self._stale_logged = False
                    backoff = WS_RECONNECT_INITIAL_DELAY

                    _LOGGER.info("EcoStream WebSocket connected: %s", self._ws_url)

                    # ------------------------------
                    # READ LOOP
                    # ------------------------------
                    while True:
                        if self._stopping:
                            break

                        # Turn coroutine into a Task (required for asyncio.wait)
                        receive_task = asyncio.create_task(ws.receive())

                        try:
                            done, _ = await asyncio.wait(
                                {receive_task},
                                timeout=WS_HEARTBEAT_INTERVAL,
                                return_when=asyncio.FIRST_COMPLETED,
                            )
                        except asyncio.CancelledError:
                            receive_task.cancel()
                            raise

                        if self._stopping:
                            receive_task.cancel()
                            break

                        # TIMEOUT → send heartbeat & stale-check
                        if not done:
                            receive_task.cancel()
                            await self._send_heartbeat()
                            if not self._stopping:
                                self._check_stale()
                            continue

                        # MESSAGE RECEIVED
                        msg = receive_task.result()

                        if msg.type == WSMsgType.TEXT:
                            self._last_message_ts = time.time()
                            self._has_received_payload = True
                            self._stale_logged = False
                            if not self._stopping:
                                await self._handle_text(msg.data)

                        elif msg.type == WSMsgType.BINARY:
                            _LOGGER.debug("Ignoring binary WS message from EcoStream")

                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING):
                            _LOGGER.warning(
                                "EcoStream WS closing (type=%s)", msg.type
                            )
                            break

                        elif msg.type == WSMsgType.ERROR:
                            _LOGGER.error(
                                "EcoStream WebSocket error: %s", ws.exception()
                            )
                            break

                        if not self._stopping:
                            self._check_stale()

            except asyncio.CancelledError:
                _LOGGER.debug("EcoStream WS loop cancelled for %s", self._host)
                break

            except (ClientError, OSError) as err:
                if not self._stopping:
                    _LOGGER.warning(
                        "EcoStream WS client/OS error: %s — reconnecting in %ss",
                        err,
                        backoff,
                    )

            except Exception as err:  # noqa: BLE001
                if not self._stopping:
                    _LOGGER.exception("Unexpected error in EcoStream WS loop: %s", err)

            finally:
                self._ws = None

            if self._stopping:
                break

            # Exponential backoff between reconnect attempts
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, WS_RECONNECT_MAX_DELAY)

    # ------------------------------------------------------------------
    # Heartbeat / stale checking
    # ------------------------------------------------------------------

    async def _send_heartbeat(self) -> None:
        """Send lightweight application-level heartbeat."""
        if self._stopping or not self._ws:
            return
        try:
            await self._ws.send_str("{}")
            _LOGGER.debug("EcoStream heartbeat → %s", self._host)
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "Failed to send EcoStream heartbeat → %s", self._host, exc_info=True
            )

    def _check_stale(self) -> None:
        """Reconnect if too long without data — only after first payload."""
        if self._stopping:
            return
        if not self._has_received_payload:
            # Avoid reconnect storms during startup / idle
            return
        if not self._ws or not self._last_message_ts:
            return

        elapsed = time.time() - self._last_message_ts
        if elapsed > WS_STALE_TIMEOUT:
            if not self._stale_logged:
                _LOGGER.warning(
                    "No EcoStream data for %.0fs (> %ss). Forcing reconnect.",
                    elapsed,
                    WS_STALE_TIMEOUT,
                )
                self._stale_logged = True

            ws = self._ws
            if ws and not ws.closed:
                # Closing triggers exit from read-loop and reconnect in _run
                self._hass.loop.create_task(ws.close())

    # ------------------------------------------------------------------
    # JSON handling
    # ------------------------------------------------------------------

    async def _handle_text(self, data: str) -> None:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            _LOGGER.warning("Invalid JSON from EcoStream: %s", data)
            return

        if not isinstance(payload, dict):
            _LOGGER.debug("Ignoring non-dict JSON from EcoStream: %s", payload)
            return

        _LOGGER.debug("WS JSON from %s: %s", self._host, payload)

        try:
            await self._message_callback(payload)
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception(
                "Error while processing EcoStream payload in coordinator: %s", err
            )
