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
from typing import Callable

import httpx
import websockets
from PySide6.QtCore import QObject, Signal

from hydra_suite.models import HydraState, RobotView, ServerInfo

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
        # This session's role ('admin' | 'operator'), from /api/login's own
        # response - same field HYDRA-UMC STUDIO's store.tsx now reads too
        # (decodeJwtRole()). Gates the Ecosystem > Connected Apps / Server
        # Logs / Server Admin panels the same way server.ts's own
        # requireAdmin already gates their backing routes.
        self.role: str | None = None
        # Per-robot generation counter guarding send_command()'s own
        # rollback-on-failure - see that method's own comment and its
        # HYDRA-UMC-IOS-CONTROL/ANDROID-CONTROL/DSI/STUDIO equivalents for
        # the full reasoning (a rapid sequence of commands for the same
        # robot can be in flight at once; an early one failing after a
        # later one already applied must not roll back over that newer
        # state).
        self._command_generation: dict[int, int] = {}

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
        self.role = data.get("role") if isinstance(data.get("role"), str) else None
        self.login_ok = True
        self.login_changed.emit(True, "")
        return True

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def _request_json(
        self, method: str, path: str, *, auth: bool = False, params: dict | None = None, json_body: dict | None = None
    ) -> tuple[int, object] | None:
        """Shared plumbing for the Ecosystem/Admin panels' own on-demand
        fetches below (GET /api/ecosystem/status, /api/telemetry/*,
        /api/admin/*) - these are one-shot reads/writes a panel's own
        Refresh/Run button triggers, not part of the continuously-synced
        HydraState this class exists to maintain, so they stay separate
        rather than folded into fetch_state()/push_state().

        Returns (status_code, parsed_body) on any real HTTP response (even
        a 4xx/5xx one - the caller decides what a given status means, same
        as login()'s own httpx.HTTPError handling does NOT apply here:
        raise_for_status() is deliberately never called), or None only on a
        genuine network failure (unreachable host, timeout, malformed
        JSON) - the same "None = best-effort read failed" convention
        fetch_system_metrics() already uses.
        """
        try:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                resp = await client.request(
                    method,
                    f"{self.info.base_url}{path}",
                    params=params,
                    json=json_body,
                    headers=self._auth_headers() if auth else None,
                    timeout=5.0,
                )
                body = resp.json()
        except (httpx.HTTPError, ValueError):
            return None
        return resp.status_code, body

    async def fetch_ecosystem_status(self) -> tuple[int, object] | None:
        """GET /api/ecosystem/status - no auth required server-side (same
        trust tier as fetch_system_metrics() above)."""
        return await self._request_json("GET", "/api/ecosystem/status")

    async def fetch_telemetry_query(self, params: dict) -> tuple[int, object] | None:
        """GET /api/telemetry/query - authenticated proxy to
        HYDRA-UMC-DATALAKE through Server (see server.ts's own
        DATALAKE_URL/proxyToDatalake()). A 503 with {"available": false}
        means Server has no HYDRA_UMC_DATALAKE_URL configured, not a
        transient failure - the caller distinguishes that from a genuine
        network error (None) or any other status."""
        return await self._request_json("GET", "/api/telemetry/query", auth=True, params=params)

    async def fetch_telemetry_aggregate(self, params: dict) -> tuple[int, object] | None:
        """Same contract as fetch_telemetry_query() above, against
        /api/telemetry/aggregate."""
        return await self._request_json("GET", "/api/telemetry/aggregate", auth=True, params=params)

    async def fetch_admin_clients(self) -> tuple[int, object] | None:
        """GET /api/admin/clients (admin-only server-side - a non-admin
        session gets a real 403 here, not a partial/empty list)."""
        return await self._request_json("GET", "/api/admin/clients", auth=True)

    async def fetch_admin_logs(self, lines: int = 300) -> tuple[int, object] | None:
        """GET /api/admin/logs (admin-only)."""
        return await self._request_json("GET", "/api/admin/logs", auth=True, params={"lines": lines})

    async def fetch_admin_server_config(self) -> tuple[int, object] | None:
        """GET /api/admin/server-config (admin-only)."""
        return await self._request_json("GET", "/api/admin/server-config", auth=True)

    async def save_admin_server_port(self, port: int) -> tuple[int, object] | None:
        """PUT /api/admin/server-config (admin-only) - see server.ts's own
        resolvePort() comment for why this needs a restart to take
        effect; it never rebinds the running listener."""
        return await self._request_json("PUT", "/api/admin/server-config", auth=True, json_body={"port": port})

    async def fetch_hydra_info(self) -> tuple[int, object] | None:
        """GET /api/hydra-info - no auth required (same discovery/identity
        route ServerInfo.from_hydra_info() already parses at scan time,
        see server_browser.py). Used here for a live re-fetch - product,
        appVersion, uptime, controller/robot counts - so AdminServerPanel
        can show a real snapshot alongside the port-config form, matching
        STUDIO's own 0.2.9 redesign."""
        return await self._request_json("GET", "/api/hydra-info")

    async def restart_server(self) -> tuple[int, object] | None:
        """POST /api/admin/restart (admin-only) - graceful self-restart,
        only meaningful behind a process supervisor configured to
        auto-restart on exit (systemd/pm2/Docker) - see server.ts's own
        comment on that route."""
        return await self._request_json("POST", "/api/admin/restart", auth=True)

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

    async def send_command(
        self,
        robot_id: int,
        command: str,
        params: dict | None = None,
        local_mutate: Callable[[RobotView], None] | None = None,
    ) -> None:
        """POSTs the atomic /api/robot/:id/command instead of push_state()'s
        own full-tree read-modify-write - for the handful of discrete
        actions that already have an exact 1:1 case in server.ts's own
        switch (today: speed/acceleration from robot_control.py's sliders).
        See DISEÑO_SYNC_DELTAS.txt CAUSA A and HYDRA-UMC-STUDIO's own
        store.tsx sendRobotCommand(), the same fix mirrored here.

        `local_mutate`, when given, applies an OPTIMISTIC local update to
        the target robot's own raw dict immediately, before the network
        round-trip even starts - same pattern as HYDRA-UMC-IOS-CONTROL/
        ANDROID-CONTROL/DSI/STUDIO's own equivalents. A failed request
        rolls the mutation back UNLESS a newer command for that same robot
        already started since (the same generation-counter guard those
        clients use - see _command_generation's own comment). Omitting
        `local_mutate` keeps the old behavior: no local mutation at all,
        state updates once the server's own broadcast/delta round-trip
        lands (self.state is otherwise never touched directly here).
        Errors are surfaced via `error` rather than raised, matching
        push_state()'s own reasoning (this is always fired via
        asyncio.ensure_future() and never awaited by its caller)."""
        snapshot_json: str | None = None
        my_generation: int | None = None
        if local_mutate is not None:
            active = self.state.active_controller
            target = active.robot_by_id(str(robot_id)) if active is not None else None
            if target is not None:
                snapshot_json = json.dumps(target.raw, sort_keys=True)
                self._command_generation[robot_id] = self._command_generation.get(robot_id, 0) + 1
                my_generation = self._command_generation[robot_id]
                local_mutate(target)
                self.state_changed.emit(self.state)

        def rollback_if_current() -> None:
            # Skip the rollback if a newer command for this same robot has
            # already started since this one's snapshot was taken - this
            # failure is stale, and restoring its snapshot now would
            # overwrite whatever that newer command already applied.
            if snapshot_json is None or self._command_generation.get(robot_id) != my_generation:
                return
            active = self.state.active_controller
            target = active.robot_by_id(str(robot_id)) if active is not None else None
            if target is not None:
                target.raw.clear()
                target.raw.update(json.loads(snapshot_json))
                self.state_changed.emit(self.state)

        try:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                resp = await client.post(
                    f"{self.info.base_url}/api/robot/{robot_id}/command",
                    json={"command": command, "params": params or {}},
                    headers=self._auth_headers(),
                    timeout=5.0,
                )
                if resp.status_code in (401, 403):
                    self.error.emit("Command rejected: not authenticated (token missing/expired)")
                    rollback_if_current()
                    return
                resp.raise_for_status()
        except (httpx.HTTPError, OSError) as e:
            self.error.emit(f"Command failed: {e}")
            rollback_if_current()

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
        # A real targeted delta (server.ts's own broadcastRobotDelta(),
        # sent only to a connection that declared schema 2 - see
        # ServerInfo.ws_url()'s own comment) - handled separately from the
        # full-tree branch below, which stays exactly as it was for a
        # schema-1 "delta"/"settings" message.
        if msg.get("type") == "delta" and msg.get("schema") == 2 and "robotId" in msg:
            self._apply_robot_delta(msg)
            return
        # "delta" (schema 1 - a full-tree write from a client that didn't
        # ask for the real delta, or an older server) and "settings" (a
        # full POST /api/settings write) carry the SAME full-tree payload
        # shape - only the label differs, see server.ts's own
        # broadcastSettings() - so both apply identically here. A command
        # sent via the atomic endpoint by another client (e.g. the Android
        # app) needs to update this mirror exactly the same way a full
        # settings write does, or a robot move made from another client
        # would never show up here live.
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

    def _apply_robot_delta(self, msg: dict) -> None:
        """Applies one {controllerId, robotId, patch, cameraId?, cameraPatch?}
        delta in place onto self.state's own raw dict (HydraState wraps a
        mutable dict - see models.py's own header comment, every RobotView/
        CameraView already mutates through to the same underlying object).

        Validates the robot exists locally BEFORE touching anything: if it
        doesn't (this mirror is stale, or somehow missed the robot's own
        initial full-tree load), the delta is discarded and a full
        fetch_state() is forced instead of ever creating a "ghost" robot
        from a partial patch - DISEÑO_SYNC_DELTAS.txt section 5b mitigation
        (b), non-optional. Deliberately does NOT update _last_payload_json -
        that guard exists to break the full-tree echo loop (push_state()'s
        own comment); a delta's own small payload was never compared
        against it in the first place, so there's nothing here to
        de-duplicate against."""
        controller_id = msg.get("controllerId")
        robot_id = msg.get("robotId")
        patch = msg.get("patch")
        if not isinstance(controller_id, str) or not isinstance(patch, dict):
            return
        target_robot: dict | None = None
        target_camera: dict | None = None
        for c in self.state.raw.get("controllers") or []:
            if str(c.get("id", "")) != controller_id:
                continue
            for r in c.get("robots") or []:
                if r.get("id") == robot_id:
                    target_robot = r
                    break
            camera_id = msg.get("cameraId")
            if camera_id is not None:
                for cam in c.get("cameras") or []:
                    if cam.get("id") == camera_id:
                        target_camera = cam
                        break
            break
        if target_robot is None:
            logger.info("HydraConnection %s: delta for unknown robot %r - forcing full reload", self.info.host, robot_id)
            asyncio.ensure_future(self.fetch_state())
            return
        target_robot.update(patch)
        camera_patch = msg.get("cameraPatch")
        if target_camera is not None and isinstance(camera_patch, dict):
            target_camera.update(camera_patch)
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
