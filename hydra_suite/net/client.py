# =============================================================================
# HYDRA-UMC SUITE - net/client.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# One HydraConnection per connected HYDRA-UMC server - this IS the "swarm"
# support: the UI holds a dict of these, one per server the user has
# added, each independently connected/live-synced. Implements exactly the
# contract in HYDRA-UMC-SERVER/docs/REMOTE_API.md (that headless backend's
# own repo since it was split out of HYDRA-UMC-STUDIO - the contract
# itself is unchanged, only which repo hosts server.ts/this doc):
# GET/POST /api/settings for the full read-modify-write cycle, and a
# WebSocket /ws connection for live push - the server broadcasts every
# change (from ANY client, including this one) to every connected client,
# so a job/parameter changed from HYDRA-UMC STUDIO's own browser UI (now a
# pure client of HYDRA-UMC-SERVER, same as this app) shows up here live,
# and a change made here shows up there live too.
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
# Same cadence HYDRA-UMC-STUDIO's own new footer (Dashboard.tsx SystemMetricsBar)
# and the Android app's own System Health panel already poll at - deliberately
# kept in sync across the ecosystem's 3 clients rather than picked independently.
METRICS_POLL_S = 5.0

# Self-identifies this client to server.ts's own per-client remote-access
# toggles (Config > Remote Access in the browser UI) - lets the project
# owner disable SUITE's own access without also blocking the Android/iOS
# apps, or vice versa. A request with no such header (a plain browser tab)
# is never gated by that check - see server.ts's own remoteAccessAllowed()
# for the full reasoning.
HYDRA_CLIENT_HEADERS = {"X-Hydra-Client": "suite"}


class HydraConnection(QObject):
    """Manages one server's REST + WebSocket connection and keeps a local
    HydraState mirror in sync with it in both directions."""

    state_changed = Signal(object)          # HydraState - emitted whenever fresh data arrives (initial load or a live push)
    status_changed = Signal(str)             # "connecting" | "connected" | "disconnected" | "error"
    metrics_changed = Signal(dict)           # GET /api/system/metrics response - cpu_load/memory_usage/temp/uptime/network
    error = Signal(str)
    # Separate from status_changed on purpose: "connected"/"disconnected" describe
    # the WebSocket link, but a server that's reachable and up can still refuse a
    # login outright (wrong username/password on that particular ServerInfo) - a
    # distinct signal for that lets the server list show a real "login failed"
    # state with the actual rejection detail, rather than a bad password reading
    # identical to "still connecting" because the only place carrying that
    # detail was `error`'s free-form text. Emitted once per login() attempt,
    # success or not.
    login_changed = Signal(bool, str)        # (ok, detail) - detail is "" on success

    def __init__(self, info: ServerInfo, parent: QObject | None = None):
        super().__init__(parent)
        self.info = info
        self.state = HydraState()
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._recv_task: asyncio.Task | None = None
        self._metrics_task: asyncio.Task | None = None
        self._closing = False
        # Mirrors HYDRA-UMC STUDIO's own src/store.tsx lastPayloadJsonRef
        # guard (see REMOTE_API.md section 3) - the server echoes every
        # write back to the sender too, so without this a local edit
        # would re-trigger itself as if it were a fresh external change.
        self._last_payload_json: str | None = None
        # server.ts's `authenticate` middleware unconditionally requires a
        # bearer token on POST /api/settings and the /ws upgrade (no
        # "security enabled" toggle despite what REMOTE_API.md's older wording
        # implies) - GET has no such requirement, so a connection with no
        # token can still read state, but every write 401s and the WebSocket
        # upgrade is rejected outright (code 1008) until login() succeeds.
        self._token: str | None = None
        # None = never attempted yet, then True/False after every login()
        # call - lets the server list show a real per-server "login failed"
        # state instead of every non-active server just sitting at whatever
        # the row said when it was first added (see
        # ui/panels/server_browser.py's own use of this).
        self.login_ok: bool | None = None

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._closing

    async def login(self) -> bool:
        """POSTs /api/login using self.info.username/password, stores the
        resulting token for every subsequent request. Returns False (and
        emits `error`) rather than raising, so a bad server/credentials
        doesn't take down connect()'s own caller."""
        try:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                resp = await client.post(
                    f"{self.info.base_url}/api/login",
                    json={"username": self.info.username, "password": self.info.password},
                    timeout=5.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            detail = f"Login failed: {e}"
            self.login_ok = False
            self.error.emit(detail)
            self.login_changed.emit(False, detail)
            return False
        token = data.get("token")
        if not token:
            detail = "Login failed: no token in response"
            self.login_ok = False
            self.error.emit(detail)
            self.login_changed.emit(False, detail)
            return False
        self._token = token
        self.login_ok = True
        self.login_changed.emit(True, "")
        return True

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def fetch_state(self) -> HydraState:
        """One-shot REST read - used for the initial load before the
        WebSocket connects, and as a manual "force refresh" the UI can
        offer independent of live sync. GET has no auth requirement
        server-side, so this works even if login() hasn't succeeded yet -
        only writes and the WebSocket actually need the token."""
        async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
            resp = await client.get(f"{self.info.base_url}/api/settings", headers=self._auth_headers(), timeout=5.0)
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
        round-trip), falls back to REST POST otherwise.

        Every call site (SuiteController.push_active_state()) fires this
        with asyncio.ensure_future() and never awaits or checks the
        result, so an exception raised in here would otherwise just
        become an unretrieved-task-exception logged to stderr - a jog
        slider, camera toggle, or trajectory-point apply that failed to
        reach the server would look like it worked from the UI's own
        point of view. Caught and surfaced via `error` instead, matching
        every other network call in this class. _last_payload_json is
        only updated AFTER a confirmed successful send - updating it
        beforehand (as this used to) would mark a write that actually
        failed on the wire as "already delivered" from the echo-guard's
        own point of view, silently blocking every future retry of that
        exact value (including the user just redoing the same jog) until
        an unrelated change happened to come in from elsewhere first."""
        payload = self.state.to_json_dict()
        payload_json = json.dumps(payload, sort_keys=True)
        if payload_json == self._last_payload_json:
            return  # unchanged since our own last confirmed send/receive - nothing to do
        try:
            if self._ws is not None:
                await self._ws.send(json.dumps({"type": "settings", "payload": payload}))
            else:
                async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                    resp = await client.post(
                        f"{self.info.base_url}/api/settings", json=payload, headers=self._auth_headers(), timeout=5.0
                    )
                    if resp.status_code in (401, 403):
                        self.error.emit("Write rejected: not authenticated (token missing/expired)")
                        return
                    resp.raise_for_status()
        except (httpx.HTTPError, websockets.WebSocketException, OSError) as e:
            self.error.emit(f"Write failed: {e}")
            return
        self._last_payload_json = payload_json

    async def fetch_system_metrics(self) -> dict | None:
        """GET /api/system/metrics - no auth required server-side. Returns
        None on any network error rather than raising, since this is a
        best-effort background poll, not a critical read."""
        try:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                resp = await client.get(f"{self.info.base_url}/api/system/metrics", timeout=5.0)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, ValueError):
            return None

    async def _metrics_loop(self) -> None:
        while not self._closing:
            data = await self.fetch_system_metrics()
            if data is not None:
                self.metrics_changed.emit(data)
            await asyncio.sleep(METRICS_POLL_S)

    async def connect(self) -> None:
        """Logs in, opens the WebSocket, and starts the receive loop.
        Reconnects automatically with a fixed delay on an unexpected drop (a
        HYDRA-UMC on a flaky Wi-Fi link or a machine that goes to sleep
        shouldn't require the user to manually re-add the server) - stops
        reconnecting only once disconnect() has been called explicitly."""
        self._closing = False
        self.status_changed.emit("connecting")
        await self.login()  # best-effort - fetch_state() below still works without it, just no writes/WS

        try:
            await self.fetch_state()
        except (httpx.HTTPError, ValueError) as e:
            self.status_changed.emit("error")
            self.error.emit(f"Initial fetch failed: {e}")
            # Still try the WebSocket below - a server that's up but whose
            # REST fetch raced a restart shouldn't be given up on immediately.

        self._recv_task = asyncio.ensure_future(self._run())
        self._metrics_task = asyncio.ensure_future(self._metrics_loop())

    async def _run(self) -> None:
        while not self._closing:
            if self._token is None and not await self.login():
                # No point opening a WS the server will reject with code 1008 -
                # wait and retry the login itself instead of spinning a
                # connect/reject loop against a server that's simply not up yet.
                self.status_changed.emit("disconnected")
                await asyncio.sleep(RECONNECT_DELAY_S)
                continue
            try:
                # max_size=None: server.ts sends the FULL settings.json (1.6MB+
                # on a populated swarm, and only grows with more robots/
                # trajectory points) as the very first WS message on every
                # connect. The websockets library's own default max_size
                # (1 MiB) rejects that with a 1009 "message too big" close
                # before this app ever sees a single byte of real state over
                # the socket - the initial REST fetch_state() above has no such
                # limit, so a cap here would be easy to miss without watching
                # the WS itself carefully. No cap here mirrors what a browser
                # WebSocket client does (no hard message size limit of its
                # own) - the real fix for the underlying payload size is a
                # smaller wire format server-side, not a client-side ceiling
                # that just moves where it breaks.
                async with websockets.connect(self.info.ws_url(self._token), open_timeout=5.0, max_size=None) as ws:
                    self._ws = ws
                    self.status_changed.emit("connected")
                    async for raw in ws:
                        self._handle_message(raw)
            except (websockets.WebSocketException, OSError) as e:
                logger.info("HydraConnection %s: WebSocket dropped (%s)", self.info.host, e)
                # A rejected/expired token surfaces as a closed connection here,
                # not an exception with a status code - force a fresh login on
                # the next loop iteration rather than retrying the same
                # (possibly now-invalid) token forever.
                self._token = None
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
        if not isinstance(msg, dict):
            return
        if msg.get("error"):
            logger.warning("HydraConnection %s: %s", self.info.host, msg["error"])
            return
        # "delta" (a write via the atomic POST /api/robot/:id/command) and
        # "settings" (a full POST /api/settings write) carry the SAME full-tree
        # payload shape - only the label differs, see server.ts's own
        # broadcastSettings() - so both apply identically here. A command sent
        # via the atomic endpoint by another client (e.g. the Android app)
        # needs to update this mirror exactly the same way a full settings
        # write does, or a robot move made from another client would never
        # show up here live.
        if msg.get("type") not in ("settings", "delta"):
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
        if self._metrics_task is not None:
            self._metrics_task.cancel()
        self.status_changed.emit("disconnected")
