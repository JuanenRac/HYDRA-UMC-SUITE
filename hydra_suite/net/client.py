# =============================================================================
# HYDRA-UMC SUITE - net/client.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# One HydraConnection per connected HYDRA-UMC server - this IS the "swarm"
# support: the UI holds a dict of these, one per server the user has
# added, each independently connected/live-synced. Implements exactly the
# contract in HYDRA-UMC-STUDIO/docs/REMOTE_API.md: GET/POST /api/settings
# for the full read-modify-write cycle, and a WebSocket /ws connection for
# live push - the server broadcasts every change (from ANY client,
# including this one) to every connected client, so a job/parameter
# changed from HYDRA-UMC STUDIO's own browser UI shows up here live, and
# a change made here shows up there live too.
#
# Runs on Qt's own event loop via qasync (see main.py) - async methods
# here are plain coroutines, no separate thread or thread-safe queue
# needed to get back onto the Qt thread, since qasync makes asyncio and
# Qt share the same loop.
# =============================================================================
from __future__ import annotations

import asyncio
import json
import logging

import httpx
import websockets
from PySide6.QtCore import QObject, Signal

from hydra_suite.models import HydraState, ServerInfo

logger = logging.getLogger(__name__)

RECONNECT_DELAY_S = 3.0


class HydraConnection(QObject):
    """Manages one server's REST + WebSocket connection and keeps a local
    HydraState mirror in sync with it in both directions."""

    state_changed = Signal(object)          # HydraState - emitted whenever fresh data arrives (initial load or a live push)
    status_changed = Signal(str)             # "connecting" | "connected" | "disconnected" | "error"
    error = Signal(str)

    def __init__(self, info: ServerInfo, parent: QObject | None = None):
        super().__init__(parent)
        self.info = info
        self.state = HydraState()
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._recv_task: asyncio.Task | None = None
        self._closing = False
        # Mirrors HYDRA-UMC STUDIO's own src/store.tsx lastPayloadJsonRef
        # guard (see REMOTE_API.md section 3) - the server echoes every
        # write back to the sender too, so without this a local edit
        # would re-trigger itself as if it were a fresh external change.
        self._last_payload_json: str | None = None

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._closing

    async def fetch_state(self) -> HydraState:
        """One-shot REST read - used for the initial load before the
        WebSocket connects, and as a manual "force refresh" the UI can
        offer independent of live sync."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.info.base_url}/api/settings", timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
        self.state = HydraState(data)
        self._last_payload_json = json.dumps(data, sort_keys=True)
        self.state_changed.emit(self.state)
        return self.state

    async def push_state(self) -> None:
        """Writes the current local HydraState back - read-modify-write,
        same as HYDRA-UMC STUDIO's own browser UI (REMOTE_API.md section
        2). Sends over the WebSocket if it's open (avoids a second HTTP
        round-trip), falls back to REST POST otherwise."""
        payload = self.state.to_json_dict()
        payload_json = json.dumps(payload, sort_keys=True)
        if payload_json == self._last_payload_json:
            return  # unchanged since our own last send/receive - nothing to do
        self._last_payload_json = payload_json
        if self._ws is not None:
            await self._ws.send(json.dumps({"type": "settings", "payload": payload}))
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.info.base_url}/api/settings", json=payload, timeout=5.0)
                resp.raise_for_status()

    async def connect(self) -> None:
        """Opens the WebSocket and starts the receive loop. Reconnects
        automatically with a fixed delay on an unexpected drop (a HYDRA-UMC
        on a flaky Wi-Fi link or a machine that goes to sleep shouldn't
        require the user to manually re-add the server) - stops
        reconnecting only once disconnect() has been called explicitly."""
        self._closing = False
        self.status_changed.emit("connecting")
        try:
            await self.fetch_state()
        except (httpx.HTTPError, ValueError) as e:
            self.status_changed.emit("error")
            self.error.emit(f"Initial fetch failed: {e}")
            # Still try the WebSocket below - a server that's up but whose
            # REST fetch raced a restart shouldn't be given up on immediately.

        self._recv_task = asyncio.ensure_future(self._run())

    async def _run(self) -> None:
        while not self._closing:
            try:
                async with websockets.connect(self.info.ws_url, open_timeout=5.0) as ws:
                    self._ws = ws
                    self.status_changed.emit("connected")
                    async for raw in ws:
                        self._handle_message(raw)
            except (websockets.WebSocketException, OSError) as e:
                logger.info("HydraConnection %s: WebSocket dropped (%s)", self.info.host, e)
            finally:
                self._ws = None
            if self._closing:
                break
            self.status_changed.emit("disconnected")
            await asyncio.sleep(RECONNECT_DELAY_S)

    def _handle_message(self, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
        except ValueError:
            logger.warning("HydraConnection %s: malformed WS message", self.info.host)
            return
        if not isinstance(msg, dict) or msg.get("type") != "settings":
            return
        payload = msg.get("payload")
        if not isinstance(payload, dict):
            return
        payload_json = json.dumps(payload, sort_keys=True)
        if payload_json == self._last_payload_json:
            return  # our own echoed-back write - see push_state()'s own comment
        self._last_payload_json = payload_json
        self.state = HydraState(payload)
        self.state_changed.emit(self.state)

    async def disconnect(self) -> None:
        self._closing = True
        if self._ws is not None:
            await self._ws.close()
        if self._recv_task is not None:
            self._recv_task.cancel()
        self.status_changed.emit("disconnected")
