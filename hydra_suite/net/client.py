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
import os
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx
import websockets
from PySide6.QtCore import QObject, Signal

from hydra_suite import access, command_sequence
from hydra_suite.panel_logic import submitted_models
from hydra_suite.panel_logic.totp import normalize_code
from hydra_suite.i18n import _
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

# A finite ceiling for one WebSocket message (the full settings tree is a few
# MB): enough for any real payload, not enough to exhaust the PC's memory.
WS_MAX_MESSAGE_BYTES = 128 * 1024 * 1024
# Server error codes (auth middleware) that a fresh login/refresh can cure.
_RENEWABLE_TOKEN_CODES = ("TOKEN_EXPIRED", "TOKEN_INVALID")

# The global STOP (POST /api/stop-all) answers fast or not at all: a stop is
# never worth waiting 5 s for, so it gets a short timeout and one retry.
STOP_ALL_TIMEOUT_S = 2.0
STOP_ALL_RETRY_DELAY_S = 0.3


@dataclass
class StopAllRobot:
    """What the server did to one robot when the global STOP reached it."""

    robot_id: int
    controller_id: str = ""
    name: str = ""
    stopped: bool = False
    valves_off: bool = False
    pumps_off: bool = False
    # The account holding the reservation, when it is somebody else (the
    # stop ignores reservations, but the operator should know).
    reserved_by: str | None = None
    error: str | None = None


@dataclass
class StopAllResult:
    """The server's answer to the global STOP, or - when nothing confirmed
    it - a result with `confirmed=False` and the reason."""

    success: bool = False
    stopped_count: int = 0
    failed_count: int = 0
    # False when the server stopped the robots but could not save the stopped state.
    persisted: bool = False
    robots: list[StopAllRobot] = field(default_factory=list)
    # True when the answer was built by stopping the robots one by one
    # (the global call was rate limited).
    via_fallback: bool = False
    confirmed: bool = True
    reason: str = ""

    @property
    def is_clean(self) -> bool:
        """Everything went as it should: confirmed, no robot failed, stopped state saved."""
        return self.confirmed and self.success and self.failed_count == 0 and self.persisted

    @property
    def failed_robots(self) -> list[StopAllRobot]:
        return [r for r in self.robots if not r.stopped]

    @classmethod
    def not_confirmed(cls, reason: str) -> "StopAllResult":
        return cls(confirmed=False, reason=reason)

    @classmethod
    def from_json(cls, body: dict) -> "StopAllResult":
        robots: list[StopAllRobot] = []
        listed = body.get("robots")
        for item in listed if isinstance(listed, list) else []:
            if not isinstance(item, dict):
                continue
            reserved = item.get("reservedBy")
            error = item.get("error")
            robots.append(
                StopAllRobot(
                    robot_id=_whole_number(item.get("robotId")),
                    controller_id=str(item.get("controllerId") or ""),
                    name=str(item.get("name") or ""),
                    stopped=bool(item.get("stopped", False)),
                    valves_off=bool(item.get("valvesOff", False)),
                    pumps_off=bool(item.get("pumpsOff", False)),
                    reserved_by=reserved if isinstance(reserved, str) and reserved else None,
                    error=error if isinstance(error, str) and error else None,
                )
            )
        failed = body["failedCount"] if isinstance(body.get("failedCount"), int) else sum(1 for r in robots if not r.stopped)
        stopped = body["stoppedCount"] if isinstance(body.get("stoppedCount"), int) else sum(1 for r in robots if r.stopped)
        return cls(
            success=bool(body.get("success", False)),
            stopped_count=stopped,
            failed_count=failed,
            persisted=bool(body.get("persisted", False)),
            robots=robots,
        )


def _whole_number(value: object) -> int:
    """A robot id as the server sent it, or 0 when it is not a whole number: a
    STOP answer must never be lost to one odd field."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return 0
    try:
        return int(value)
    except (ValueError, OverflowError):
        return 0


def is_settings_tree(data: object) -> bool:
    """True when `data` has the shape of the settings tree every panel reads:
    an object whose controllers (when present) are objects holding robot and
    camera lists of objects. Anything else is not allowed to replace the
    state, whoever sent it."""
    if not isinstance(data, dict):
        return False
    controllers = data.get("controllers")
    if controllers is None:
        return True
    if not isinstance(controllers, list):
        return False
    for controller in controllers:
        if not isinstance(controller, dict):
            return False
        for key in ("robots", "cameras"):
            items = controller.get(key)
            if items is not None and (not isinstance(items, list) or not all(isinstance(i, dict) for i in items)):
                return False
    return True


def _body_code(resp: "httpx.Response") -> str | None:
    try:
        body = resp.json()
    except ValueError:
        return None
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, str) else None


def _body_error(resp: "httpx.Response") -> str:
    try:
        body = resp.json()
    except ValueError:
        return f"HTTP {resp.status_code}"
    detail = body.get("error") if isinstance(body, dict) else None
    return detail if isinstance(detail, str) and detail else f"HTTP {resp.status_code}"


def describe_rejection(resp: "httpx.Response", what: str) -> str:
    """The message for a 4xx answer to a write: a stale session, a missing
    permission, a refused command (400), a jog that was not armed, and a robot
    reserved by another account, by the same account on another controller or
    by a controller this request did not name (409) each read differently to
    the operator."""
    status = resp.status_code
    code = _body_code(resp)
    if status == 401 or (status == 403 and code in _RENEWABLE_TOKEN_CODES):
        return _("MSG_NET_REJ_AUTH", what=what)
    if status == 412 or code == "revision-mismatch":
        return _("MSG_NET_REJ_REVISION", what=what)
    if code == "stale-sequence":
        return _("MSG_NET_REJ_STALE", what=what)
    if code == "jog-not-armed":
        return _("MSG_NET_REJ_NOT_ARMED", what=what, detail=_body_error(resp))
    if status == 423 or code == "robot-disabled":
        return _("MSG_NET_REJ_DISABLED", what=what, detail=_body_error(resp))
    if code == "controller-id-required":
        return _("MSG_NET_REJ_CONTROLLER_REQUIRED", what=what, detail=_body_error(resp))
    if status == 403:
        return _("MSG_NET_REJ_DENIED", what=what, detail=_body_error(resp))
    if status == 409:
        if code == "other-account":
            return _("MSG_NET_REJ_OTHER_ACCOUNT", what=what, detail=_body_error(resp))
        if code == "other-controller":
            return _("MSG_NET_REJ_OTHER_CONTROLLER", what=what, detail=_body_error(resp))
        return _("MSG_NET_REJ_RESERVED", what=what, detail=_body_error(resp))
    if status == 400:
        return _("MSG_NET_REJ_BAD", what=what, detail=_body_error(resp))
    return _("MSG_NET_FAILED_HTTP", what=what, status=status)


@dataclass
class AccessResult:
    """The answer of a reservation, arming or limits request: `code` is "" on success, otherwise one of
    access.failure_code_for()'s codes; `detail` is the server's own explanation when it gave one."""

    ok: bool
    status: int = 0
    code: str = ""
    detail: str = ""
    expires_at: float | None = None
    body: object = None


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
    claims_changed = Signal()                # the server pushed the list of reservations (WebSocket message `claims`)
    canota_progress = Signal(object)         # one progress line of a CAN flash cycle (WebSocket message `canota_progress`; admin sessions only)

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
        # Opaque refresh token from /api/login - exchanged at /api/refresh for
        # a new access token when the JWT expires, so a station left open for
        # days keeps control without asking for the password again.
        self._refresh_token: str | None = None
        self._renew_lock = asyncio.Lock()
        # True once the server answered a login with 401/403 (or there are no
        # credentials to send): retrying the same credentials only burns the
        # server's login rate limit, so the reconnect loop waits for the
        # operator to edit them (which reconnects from scratch).
        self._login_rejected = False
        # The code of the second step, typed by the operator for the next sign-in only: it is sent once and forgotten
        # (a code works once), and it is never saved. `needs_totp` is set when the server asked for it.
        self.totp_code = ""
        self.needs_totp = False
        # None = never attempted yet, then True/False after every login()
        # call - lets the server list show a real per-server "login failed"
        # state instead of every non-active server just sitting at whatever
        # the row said when it was first added (see
        # the former server browser's own use of this).
        self.login_ok: bool | None = None
        # Set only when the server's own login rate limiter (server.ts's
        # loginRateLimiter, default 5 attempts/15min/IP) rejects a login
        # with 429 - see login()'s own comment for the real bug this fixes:
        # _run()'s reconnect loop used to retry login() every
        # RECONNECT_DELAY_S regardless of WHY it failed, exhausting that
        # budget in ~15s and then looking "broken" for the full lockout
        # window on every server this app connected to.
        self._login_retry_after_s: float | None = None
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
        # Per-(robot, command-name) THROTTLE (see send_command()'s own
        # comment on why this is a throttle and not a debounce) for
        # send_command()'s own network send - a dragged RotaryKnob/QSlider
        # (the former robot control panel's JointRow/speed slider) emits continuously,
        # and until this existed each of HYDRA-UMC-ANDROID-CONTROL's own
        # equivalent sendAtomicCommand() already debounces its speed command
        # 300ms for exactly this reason - this desktop client had the same
        # gap. Keyed by (robot_id, command) - keying by command name
        # ALONE (as this used to) meant throttling 'jog' for robot 1 shared
        # the exact same timer/slot as 'jog' for robot 2, so two robots
        # jogged in the same window could silently drop one of their two
        # commands (whichever call didn't win the shared
        # _throttle_latest_send slot never reached the network at all) -
        # the same collision the header comment already correctly worried
        # about for two DIFFERENT command names, just missed for the SAME
        # command name across different robots. _throttle_tasks holds the
        # pending timer (if any); _throttle_latest_send holds the most
        # recent send_now() closure that timer will call once it fires.
        self._throttle_tasks: dict[tuple[int, str], asyncio.Task] = {}
        self._throttle_latest_send: dict[tuple[int, str], Callable[[], Awaitable[None]]] = {}
        # The limits the server reports (jog size, bed temperature, arming, mandatory
        # controller id), the reservations it lists, and until when the jog of each robot
        # is armed - refreshed by refresh_access(), never guessed.
        self.safety = access.SafetyState()
        self.claims: list[access.ClaimEntry] = []
        self.jog_armed_until: dict[int, float | None] = {}
        # The revision last seen of each robot (If-Match on the writes) and when the server last pushed the
        # reservations (time.monotonic()), so the poll of GET /api/claims can rest while the pushes arrive.
        self.revisions = access.RevisionTracker()
        # An operator's edit of the settings tree is not sent (the server takes it only from an administrator): said once.
        self._operator_edit_told = False
        self.claims_pushed_at = 0.0
        self.last_canota_progress: dict | None = None  # the latest progress line of a CAN flash cycle, None before the first
        # Whether the server was last seen to understand the "table" command (true until it says otherwise).
        self.has_table_command = True

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._closing

    async def login(self) -> bool:
        """POSTs /api/login using self.info.username/password, stores the
        resulting token for every subsequent request. Returns False (and
        emits `error`) rather than raising, so a bad server/credentials
        doesn't take down connect()'s own caller."""
        if not self.info.username or not self.info.password:
            # A server found by the scan has no credentials yet: nothing is
            # sent (an empty login only counts against the server's rate
            # limit, shared with every other client on this PC).
            detail = "Enter the username and password for this server"
            self._login_rejected = True
            self.login_ok = False
            self.login_changed.emit(False, detail)
            return False
        try:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                login_body = {"username": self.info.username, "password": self.info.password}
                code_sent = bool(self.totp_code.strip())
                if code_sent:
                    login_body["totp"] = normalize_code(self.totp_code)
                self.totp_code = ""
                resp = await client.post(
                    f"{self.info.base_url}/api/login",
                    json=login_body,
                    timeout=5.0,
                )
                if resp.status_code == 429:
                    # Real bug found live: server.ts's own loginRateLimiter
                    # (default 5 attempts/15min/IP) tripped, and this
                    # class's own _run() reconnect loop was retrying
                    # login() every RECONNECT_DELAY_S with no backoff -
                    # wrong credentials (or a server that was briefly down
                    # mid reconnect burst) exhausted that budget in ~15s,
                    # then looked "broken" for the full 15-minute lockout,
                    # on every server this app connected to. The 429 body
                    # already carries retryAfterMs specifically for a
                    # well-behaved client to honor (see that handler's own
                    # comment) - _run() now sleeps that long instead of
                    # blindly retrying into the same lockout.
                    try:
                        body = resp.json()
                    except ValueError:
                        body = None
                    retry_after_ms = body.get("retryAfterMs") if isinstance(body, dict) else None
                    self._login_retry_after_s = (
                        float(retry_after_ms) / 1000 if isinstance(retry_after_ms, (int, float)) else RECONNECT_DELAY_S
                    )
                    detail = (body.get("error") if isinstance(body, dict) else None) or _("MSG_NET_TOO_MANY_LOGINS")
                    self.login_ok = False
                    self.error.emit(detail)
                    self.login_changed.emit(False, detail)
                    return False
                if resp.status_code in (400, 401, 403):
                    self._login_rejected = True
                    detail = _body_error(resp)
                    try:
                        refusal = resp.json()
                    except ValueError:
                        refusal = None
                    self.needs_totp = isinstance(refusal, dict) and refusal.get("totpRequired") is True
                    if self.needs_totp and not code_sent:
                        # The account has the second step on: say what is needed, in the language of the program.
                        detail = _("MSG_NET_LOGIN_NEEDS_CODE")
                    self.login_ok = False
                    self.error.emit(detail)
                    self.login_changed.emit(False, detail)
                    return False
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            detail = _("MSG_NET_LOGIN_FAILED", error=e)
            self.login_ok = False
            self.error.emit(detail)
            self.login_changed.emit(False, detail)
            return False
        self._login_retry_after_s = None
        if not isinstance(data, dict):
            data = {}
        token = data.get("token")
        if not token:
            detail = _("MSG_NET_LOGIN_NO_TOKEN")
            self.login_ok = False
            self.error.emit(detail)
            self.login_changed.emit(False, detail)
            return False
        self._token = token
        refresh = data.get("refreshToken")
        self._refresh_token = refresh if isinstance(refresh, str) and refresh else None
        self._login_rejected = False
        self.role = data.get("role") if isinstance(data.get("role"), str) else None
        self.needs_totp = False
        self.login_ok = True
        self.login_changed.emit(True, "")
        return True

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def auth_headers(self) -> dict[str, str]:
        """Public: the bearer header for requests made outside this class
        (the live camera streams)."""
        return self._auth_headers()

    async def _renew_session(self, stale_token: str | None) -> bool:
        """Gets a new access token after the server said the one in use is
        expired/invalid: the refresh token first, the stored credentials as a
        fallback. Concurrent callers renew once (the second sees a token that
        already changed)."""
        async with self._renew_lock:
            if self._token is not None and self._token != stale_token:
                return True  # another request already renewed it
            if self._refresh_token:
                try:
                    async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                        resp = await client.post(
                            f"{self.info.base_url}/api/refresh", json={"refreshToken": self._refresh_token}, timeout=5.0
                        )
                    body = resp.json() if resp.status_code == 200 else None
                except (httpx.HTTPError, ValueError):
                    body = None
                if isinstance(body, dict) and isinstance(body.get("token"), str) and body["token"]:
                    self._token = body["token"]
                    new_refresh = body.get("refreshToken")
                    if isinstance(new_refresh, str) and new_refresh:
                        self._refresh_token = new_refresh
                    if isinstance(body.get("role"), str):
                        self.role = body["role"]
                    return True
            self._token = None
            self._refresh_token = None
            return await self.login()

    async def _http(
        self, method: str, path: str, *, timeout: float = 5.0, headers: dict | None = None, **kwargs
    ) -> httpx.Response:
        """One request to this server with the session's bearer token. A
        403 TOKEN_EXPIRED/TOKEN_INVALID (or a 401) renews the session once and
        repeats the request; any other answer is returned for the caller to
        interpret (it can be an ordinary role 403)."""
        used = self._token
        request_headers = dict(headers or {})
        if used:
            request_headers["Authorization"] = f"Bearer {used}"
        url = f"{self.info.base_url}{path}"
        async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
            resp = await client.request(method, url, headers=request_headers, timeout=timeout, **kwargs)
        if used and (resp.status_code == 401 or (resp.status_code == 403 and _body_code(resp) in _RENEWABLE_TOKEN_CODES)):
            if await self._renew_session(used) and self._token:
                request_headers["Authorization"] = f"Bearer {self._token}"
                async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                    resp = await client.request(method, url, headers=request_headers, timeout=timeout, **kwargs)
        return resp

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
        # The token goes with every request, `auth` or not: a server started
        # with HYDRA_UMC_INFO_AUTH=required answers 401 to the otherwise open
        # reads (metrics, supervisor, ecosystem) without it.
        try:
            resp = await self._http(method, path, params=params, json=json_body)
            body = resp.json()
        except (httpx.HTTPError, ValueError):
            return None
        return resp.status_code, body

    async def canota_request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        data: bytes | None = None,
        timeout: float = 60.0,
    ) -> tuple[int, object] | None:
        """Real GET/POST to HYDRA-UMC-SERVER's own /api/hardware/canota/*
        routes (version query, flash) - matches STUDIO's own
        hardwareQueryVersion()/hardwareStartFlash() (src/lib/canOta.ts)
        one-to-one: always sent with this connection's own auth token,
        same base_url/error-handling shape as _request_json() above. Kept
        as its own method only because a flash POST sends a raw
        application/octet-stream firmware body, not JSON - `_request_json`
        has no `data:` param for that. A real flash cycle can run long (no
        populated STM32H745 board exists yet to have actually timed one
        against - see can_ota.py's own header), so this uses a generous
        60s timeout rather than `_request_json`'s own 5s default, which
        assumes a quick settings-style round trip."""
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/octet-stream"
        try:
            resp = await self._http(method, path, params=params, content=data, headers=headers, timeout=timeout)
            body = resp.json()
        except (httpx.HTTPError, ValueError):
            return None
        return resp.status_code, body

    async def fetch_ecosystem_status(self) -> tuple[int, object] | None:
        """GET /api/ecosystem/status - no auth required server-side (same
        trust tier as fetch_system_metrics() above)."""
        return await self._request_json("GET", "/api/ecosystem/status")

    async def control_service(self, unit: str, action: str) -> tuple[int, object] | None:
        """POST /api/ecosystem/service/:unit/:action - admin-only
        server-side (see server.ts's own route comment for the real
        security boundary: `unit` is re-validated there against a fresh
        scan, never trusted from this call, and this Server's own unit is
        refused unconditionally). `action` is one of start/stop/restart -
        the caller (EcosystemServicesPanel) is the one place that builds
        this value from its own fixed 3-button set, never from anything
        the operator could otherwise type in."""
        return await self._request_json("POST", f"/api/ecosystem/service/{unit}/{action}", auth=True)

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

    async def fetch_connection_clients(self) -> tuple[int, object] | None:
        """GET /api/connections/clients (any signed-in account; a non-administrator only sees its own). A server that predates the
        history answers 404."""
        return await self._request_json("GET", "/api/connections/clients", auth=True)

    async def fetch_connection_events(self, limit: int = 30) -> tuple[int, object] | None:
        """GET /api/connections/events, newest first (the server accepts 1 to 500)."""
        return await self._request_json("GET", "/api/connections/events", auth=True, params={"limit": max(1, min(int(limit), 500))})

    async def fetch_ecosystem_health(self) -> tuple[int, object] | None:
        """GET /api/ecosystem/health (an operator or an administrator; the server answers 404 until an administrator turns the option on
        in Server Admin, and a server that predates the route answers 404 too). Read only. The status counts even when the body is not
        JSON (a plain 404 page): only a request that did not get an answer at all returns None."""
        try:
            resp = await self._http("GET", "/api/ecosystem/health")
        except httpx.HTTPError:
            return None
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, None

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

    async def put_admin_server_config(self, patch: dict) -> tuple[int, object] | None:
        """PUT /api/admin/server-config (admin-only) with one or more of the access options (aiAccess, infoAuth, tls,
        ble). The answer carries the options as the server now has them and the warnings it wants to show."""
        return await self._request_json("PUT", "/api/admin/server-config", auth=True, json_body=patch)

    async def fetch_hydra_info(self) -> tuple[int, object] | None:
        """GET /api/hydra-info - no auth required (same discovery/identity
        route ServerInfo.from_hydra_info() already parses at scan time,
        see server_browser.py). Used here for a live re-fetch - product,
        appVersion, uptime, controller/robot counts - so AdminServerPanel
        can show a real snapshot alongside the port-config form, matching
        STUDIO's own 0.2.9 redesign."""
        return await self._request_json("GET", "/api/hydra-info")

    async def fetch_system_supervisor(self) -> tuple[int, object] | None:
        """GET /api/system/supervisor - no auth required server-side (same
        "read-only host introspection" trust tier as /api/system/metrics -
        see server.ts's own route comment), the real Netdata-style
        deep-dive HYDRA-UMC-STUDIO's own SystemSupervisor.tsx already
        polls every 2s. Deliberately a plain on-demand fetch through
        _request_json() - like fetch_admin_clients()/fetch_telemetry_query()
        above, not a continuous background loop on this connection the way
        fetch_system_metrics()/_metrics_loop() is - this route runs a real
        `ps`/`df` on the host every call, so it should only ever be polled
        while SystemSupervisorPanel is actually the one asking, not for
        every connection regardless of whether anyone is looking at it."""
        return await self._request_json("GET", "/api/system/supervisor")

    async def restart_server(self) -> tuple[int, object] | None:
        """POST /api/admin/restart (admin-only) - graceful self-restart,
        only meaningful behind a process supervisor configured to
        auto-restart on exit (systemd/pm2/Docker) - see server.ts's own
        comment on that route."""
        return await self._request_json("POST", "/api/admin/restart", auth=True)

    async def fetch_camera_status(self) -> tuple[int, object] | None:
        """GET /api/cameras/status (admin-only) - real live status of
        every camera's own local `stream serve` process, keyed
        "<controllerId>:<cameraId>" (HYDRA-UMC-SERVER's own new
        per-camera process supervisor). The real "did this camera's
        config actually work" feedback the Cameras panel never had
        before - matches HYDRA-UMC-STUDIO's own Config.tsx one-to-one."""
        return await self._request_json("GET", "/api/cameras/status", auth=True)

    async def discover_rtsp_path(self, host: str, port: int, username: str, password: str) -> tuple[int, object] | None:
        """POST /api/camera/discover-rtsp-path (admin-only) - real RTSP
        DESCRIBE probing against a curated list of this ecosystem's own
        known-real paths, server-side (see server.ts's own
        RTSP_PATH_CANDIDATES/discoverRtspPath()). Never guesses a path
        client-side; the server reports exactly which real paths it
        tried either way."""
        return await self._request_json(
            "POST", "/api/camera/discover-rtsp-path", auth=True,
            json_body={"host": host, "port": port, "username": username, "password": password},
        )

    async def discover_usb_devices(self) -> tuple[int, object] | None:
        """GET /api/camera/discover-usb-devices (admin-only) - real
        cv2.VideoCapture enumeration, shelled out to
        HYDRA-UMC-VISION-STREAMER's own "discover-usb" subcommand on
        the server side - an index this reports is genuinely the same
        one "stream serve" would open, not a separate guess."""
        return await self._request_json("GET", "/api/camera/discover-usb-devices", auth=True)

    async def send_ptz(
        self, camera_id: int, host: str, username: str, password: str, pan: int, tilt: int, zoom: int
    ) -> tuple[int, object] | None:
        """POST /api/camera/:id/ptz (admin-only) - real PSIA continuous-
        move command relayed to the camera's own HTTP API, IP cameras
        only (matches HYDRA-UMC-STUDIO's own CamerasView.tsx one-to-one).
        pan/tilt/zoom each -100..100, 0/0/0 = stop. A camera with no real
        motorized PTZ hardware answers with a real error - the server
        reports it as-is, never pretends the move worked."""
        return await self._request_json(
            "POST", f"/api/camera/{camera_id}/ptz", auth=True,
            json_body={"host": host, "username": username, "password": password, "pan": pan, "tilt": tilt, "zoom": zoom},
        )

    async def take_camera_snapshot(self, camera_id: int) -> tuple[int, object] | None:
        """POST /api/camera/:id/snapshot - captures and saves one real
        frame off that camera's own local mjpeg stream. Matches
        HYDRA-UMC-STUDIO's own CamerasView.tsx takePhoto()."""
        return await self._request_json("POST", f"/api/camera/{camera_id}/snapshot", auth=True)

    async def start_camera_recording(self, camera_id: int) -> tuple[int, object] | None:
        """POST /api/camera/:id/recording/start - matches
        HYDRA-UMC-STUDIO's own CamerasView.tsx toggleRecording()."""
        return await self._request_json("POST", f"/api/camera/{camera_id}/recording/start", auth=True)

    async def stop_camera_recording(self, camera_id: int) -> tuple[int, object] | None:
        """POST /api/camera/:id/recording/stop."""
        return await self._request_json("POST", f"/api/camera/{camera_id}/recording/stop", auth=True)

    async def list_camera_media(self) -> tuple[int, object] | None:
        """GET /api/camera/media - every saved snapshot/recording across
        every camera, newest first."""
        return await self._request_json("GET", "/api/camera/media", auth=True)

    async def fetch_camera_media_bytes(self, camera_id: int, kind: str, filename: str) -> bytes | None:
        """GET /api/camera/media/:cameraId/:kind/:filename - the real raw
        bytes of one saved snapshot (a plain JPEG) or recording (raw
        multipart/x-mixed-replace framing, the same real boundary/
        Content-Length framing every live camera stream already uses -
        see the former camera_media panel's MjpegRecordingPlayer for how a
        recording's own individual frames get parsed back out of it).
        Deliberately NOT sent with an auth header - this route is
        intentionally open server-side (see server.ts's own comment on
        it: an `<img src>` cannot send one either), so this call doesn't
        need `_request_json`'s own auth plumbing at all. `None` only on a
        genuine network failure; a real 404/other status still returns
        the real bytes HYDRA-UMC-SERVER sent back (an error JSON body,
        as raw bytes) so the caller can decide what "no real image" means
        for its own UI rather than this method guessing."""
        path = f"/api/camera/media/{camera_id}/{kind}/{filename}"
        try:
            resp = await self._http("GET", path, timeout=120.0)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None  # an error body is not a picture or a recording
        return resp.content

    async def save_camera_media_to(self, camera_id: int, kind: str, filename: str, dest_path: str) -> bool:
        """Streams one saved snapshot/recording to `dest_path` in chunks, so a
        long recording neither waits for a whole-body timeout nor sits in
        memory. The bytes go to a `.part` file first and replace the
        destination only once the answer was a complete 200; an error answer,
        a network failure or an unwritable folder leaves nothing behind and
        returns False."""
        path = f"/api/camera/media/{camera_id}/{kind}/{filename}"
        part = f"{dest_path}.part"
        url = f"{self.info.base_url}{path}"
        timeout = httpx.Timeout(10.0, read=120.0)
        try:
            for attempt in (0, 1):
                used = self._token
                headers = {"Authorization": f"Bearer {used}"} if used else {}
                async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                    async with client.stream("GET", url, headers=headers, timeout=timeout) as resp:
                        if attempt == 0 and used and (resp.status_code == 401 or (resp.status_code == 403 and _body_code(await _read_json_body(resp)) in _RENEWABLE_TOKEN_CODES)):
                            pass  # renew below, then repeat once
                        elif resp.status_code != 200:
                            return False
                        else:
                            with open(part, "wb") as f:
                                async for chunk in resp.aiter_bytes(65536):
                                    f.write(chunk)
                            os.replace(part, dest_path)
                            return True
                if not (await self._renew_session(used) and self._token):
                    return False
            return False
        except (httpx.HTTPError, OSError):
            return False
        finally:
            try:
                os.remove(part)
            except OSError:
                pass

    async def delete_camera_media(self, camera_id: int, kind: str, filename: str) -> tuple[int, object] | None:
        """DELETE /api/camera/media/:cameraId/:kind/:filename - a real,
        permanent delete (admin-only server-side). Matches
        HYDRA-UMC-STUDIO's own CameraMediaView.tsx deleteSelected()."""
        return await self._request_json("DELETE", f"/api/camera/media/{camera_id}/{kind}/{filename}", auth=True)

    async def fetch_works_index(self, folder_path: str) -> tuple[int, object] | None:
        """GET /<folderPath>/index.json - the same static file
        HYDRA-UMC-STUDIO's own RobotDetail.tsx fetchWorks() reads
        (server.ts serves `dataPath` under express.static, no /api
        prefix). No auth - the file itself carries nothing sensitive,
        same trust tier STUDIO's own fetch() already assumes. Returns
        (200, list[str]) on a real folder, or None on a genuine network
        failure; a folder that doesn't exist yet answers 404, which the
        caller treats as "no Works recorded here yet", not an error."""
        return await self._request_json("GET", f"/{folder_path}/index.json")

    async def fetch_work_file(self, folder_path: str, file_name: str) -> tuple[int, object] | None:
        """GET /<folderPath>/<fileName> - one real trajectory file in
        HYDRA-UMC-STUDIO's own WORKS/*.json format (a plain JSON array of
        points, each either native j1..j6 joints or an x/y/z(/a/b/c)
        Cartesian pose - see server.ts's own POST /api/robot/:id/command
        trajectory validation for the exact accepted shape)."""
        return await self._request_json("GET", f"/{folder_path}/{file_name}")

    async def save_work_file(self, folder_path: str, file_name: str, content: list[dict]) -> tuple[int, object] | None:
        """POST /api/upload-work (authenticate-only, no admin required -
        see server.ts's own route comment on why an operator account can
        reach this) - writes `content` as `<folderPath>/<fileName>` and
        appends it to that folder's own index.json, the exact same call
        HYDRA-UMC-STUDIO's own RobotDetail.tsx handleSaveWorkFile() makes.
        `content` must already be in STUDIO's own WORKS point shape
        (native j1..j6 joints, which is exactly what this app's own
        RobotView.joints/the former trajectory panel already record - no
        Cartesian conversion needed for a point recorded here to be a
        real, playable Work on Server or in STUDIO's own browser UI)."""
        return await self._request_json(
            "POST", "/api/upload-work", auth=True,
            json_body={"folderPath": folder_path, "fileName": file_name, "content": content},
        )

    async def fetch_state(self) -> HydraState:
        """One-shot REST read - used for the initial load before the
        WebSocket connects, and as a manual "force refresh" the UI can
        offer independent of live sync. GET has no auth requirement
        server-side, so this works even if login() hasn't succeeded yet -
        only writes and the WebSocket actually need the token."""
        resp = await self._http("GET", "/api/settings")
        resp.raise_for_status()
        data = resp.json()
        if not is_settings_tree(data):
            raise ValueError("the server's settings are not a settings tree")
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
        if self.role in ("operator", "viewer"):
            # POST /api/settings and the `settings` message of the WebSocket take the whole tree from an administrator
            # only. An operator's edit used to be sent and refused after every change; it stays in this window instead,
            # and the person is told once. The robot commands (jog, play, stop, speed, table) go through the atomic route.
            if not self._operator_edit_told:
                self._operator_edit_told = True
                self.error.emit(_("MSG_NET_OPERATOR_LOCAL_ONLY"))
            return
        try:
            if self._ws is not None:
                await self._ws.send(json.dumps({"type": "settings", "payload": payload}))
            else:
                resp = await self._http("POST", "/api/settings", json=payload)
                if resp.status_code >= 400:
                    self.error.emit(describe_rejection(resp, _("MSG_NET_WHAT_WRITE")))
                    return
                # The server lowers a bed target above the ceiling of its model and says so.
                try:
                    answer = resp.json()
                except ValueError:
                    answer = None
                for warning in access.parse_warnings(answer):
                    if warning.is_temperature:
                        self.error.emit(_("MSG_NET_TEMP_LOWERED", requested=f"{warning.requested:g}" if warning.requested is not None else "?", applied=f"{warning.applied:g}" if warning.applied is not None else "?"))
        except (httpx.HTTPError, websockets.WebSocketException, OSError) as e:
            self.error.emit(_("MSG_NET_WRITE_FAILED", error=e))
            return
        self._last_payload_json = payload_json
        # Saving the whole tree changes the robots on the server too: what was known of their revisions is stale.
        self.revisions.forget()

    async def send_command(
        self,
        robot_id: int,
        command: str,
        params: dict | None = None,
        local_mutate: Callable[[RobotView], None] | None = None,
        debounce_ms: float = 0,
    ) -> None:
        """POSTs the atomic /api/robot/:id/command instead of push_state()'s
        own full-tree read-modify-write - for the handful of discrete
        actions that already have an exact 1:1 case in server.ts's own
        switch (today: jog/speed/acceleration from the former robot control panel's
        knob/sliders). See HYDRA-UMC-STUDIO's own store.tsx
        sendRobotCommand(), the same fix mirrored here.

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
        asyncio.ensure_future() and never awaited by its caller).

        `debounce_ms`, when positive, throttles only the real network POST -
        `local_mutate` above still applies immediately on every call, so a
        dragged RotaryKnob/QSlider (the former robot control panel's JointRow/speed
        controls, both of which emit continuously) still gets instant
        per-tick visual feedback. This is a real THROTTLE, not a debounce
        (see the implementation's own comment for the real bug that fixed):
        a rapid burst still collapses down to roughly one real POST per
        `debounce_ms`, but a send for this exact `command` name keeps
        firing at that steady cadence for as long as the burst continues,
        rather than only once it settles - so every other connected client
        sees the robot move smoothly WHILE it's being dragged, not just
        jump to the final value once the drag stops. Named `debounce_ms`
        for continuity with HYDRA-UMC-ANDROID-CONTROL's own
        sendAtomicCommand(debounceMs=...) and HYDRA-UMC-IOS-CONTROL/DSI's
        own RobotViewModel._sendAtomicCommand(debounce:...) - those still
        cancel-and-restart their own pending job on every call (a real
        debounce, not this throttle), which likely has the same
        continuous-drag gap for whichever of their own controls emits
        continuously; not fixed here, out of this repo's scope."""
        # A robot put in Sim never receives a command that moves it or switches something on, and a jog
        # above the limit of its model is not sent: both are refused here, before any local change or
        # network traffic, and the operator is told why.
        scope = f"{self.info.host}:{self.info.port}"
        if access.MODES.blocked(scope, [robot_id], command):
            self.error.emit(_("MSG_NET_SIM_BLOCKED", command=command, robot=robot_id))
            return
        if command in ("jog", "table"):
            active_controller = self.state.active_controller
            robot_view = active_controller.robot_by_id(str(robot_id)) if active_controller is not None else None
            model = robot_view.model if robot_view is not None else None
            if command == "jog":
                check = access.check_jog(self.safety.limits, model, params)
            else:
                # A table move is checked as a whole, and a relative one also by where it ends.
                table = robot_view.xy_table if robot_view is not None else None
                pos = table.get("pos") if isinstance(table, dict) and isinstance(table.get("pos"), dict) else {}
                check = access.check_table(self.safety.limits, model, params, {"x": pos.get("x"), "y": pos.get("y")})
            if not check.ok:
                self.error.emit(_("MSG_NET_JOG_LIMIT", limit=f"{'abs ' if check.kind == 'absolute' else ''}{check.limit:g}"))
                return
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

        async def post_command(name: str, body_params: dict) -> httpx.Response:
            """One POST of a command with the revision this program last saw of the robot as If-Match (never for
            STOP): a 412 means someone else changed the robot in between and nothing was applied."""
            ticket = self.revisions.begin(robot_id, name)
            headers = {"If-Match": ticket.if_match} if ticket.if_match else None
            try:
                resp = await self._http(
                    "POST", f"/api/robot/{robot_id}/command", headers=headers,
                    json={"command": name, "params": body_params, "controllerId": access.get_controller_id(), **command_sequence.next_for(name)},
                )
            except BaseException:
                self.revisions.finish(robot_id, ticket.seq, None)
                raise
            try:
                body = resp.json()
            except ValueError:
                body = None
            self.revisions.finish(robot_id, ticket.seq, access.revision_of(body))
            return resp

        async def send_now() -> None:
            try:
                if command == "table" and not self.has_table_command:
                    resp = await send_table_as_jogs()
                else:
                    resp = await post_command(command, params or {})
                    if command == "table" and resp.status_code == 400 and access.is_unknown_command(resp.status_code, _body_code(resp), _body_error(resp)):
                        # A server that predates the table command: remember it and do the same with the jogs it understands.
                        self.has_table_command = False
                        resp = await send_table_as_jogs()
                if resp.status_code >= 400:
                    self.error.emit(describe_rejection(resp, _("MSG_NET_WHAT_COMMAND")))
                    rollback_if_current()
                    if resp.status_code == 412:
                        # The robot changed under this program: read it again so the screen shows what it is now.
                        await self.refresh_robot(robot_id)
                    return
                warnings = self._command_warnings(resp)
                if warnings:
                    # 200 with warnings means the server applied nothing.
                    self.error.emit(_("MSG_NET_CMD_NOT_APPLIED", warnings=warnings))
                    rollback_if_current()
            except (httpx.HTTPError, OSError) as e:
                self.error.emit(_("MSG_NET_CMD_FAILED", error=e))
                rollback_if_current()

        async def send_table_as_jogs() -> httpx.Response:
            last: httpx.Response | None = None
            for jog in access.table_as_jogs(params or {}):
                last = await post_command("jog", jog)
                if last.status_code >= 400:
                    return last
            return last if last is not None else httpx.Response(200, json={"success": True})

        if debounce_ms <= 0:
            await send_now()
            return

        # Real bug found live: this used to be a genuine DEBOUNCE (cancel
        # the pending timer and restart it on every call) rather than a
        # THROTTLE - during a CONTINUOUS drag (RotaryKnob.mouseMoveEvent()/
        # QSlider.valueChanged firing faster than debounce_ms apart, which
        # a smooth mouse drag routinely does), every new tick cancelled the
        # previous timer before it ever fired, so essentially nothing
        # reached the network until the drag paused or ended. SUITE's own
        # viewport still looked perfectly smooth (local_mutate applies
        # instantly, no network round-trip needed for that), but every
        # OTHER connected client (HYDRA-UMC STUDIO's browser UI, watching
        # the same robot live) received almost nothing during the drag and
        # then jumped straight to the final value - reported live as "en
        # Studio va a trompicones" while SUITE's own view moved smoothly.
        #
        # Now a real throttle: the first call in a burst schedules exactly
        # one send `debounce_ms` out; every later call during that same
        # window only updates which `send_now` will run when it fires
        # (always the latest one - the exact command this call would have
        # sent), it does NOT reset the timer. A steady stream of drag
        # events now reaches every other client at a steady ~debounce_ms
        # cadence for as long as the drag continues, instead of only once
        # it stops.
        throttle_key = (robot_id, command)
        self._throttle_latest_send[throttle_key] = send_now
        pending = self._throttle_tasks.get(throttle_key)
        if pending is not None and not pending.done():
            return  # a timer for this (robot, command) is already ticking - it will pick up the latest send_now above when it fires

        async def fire_throttled() -> None:
            await asyncio.sleep(debounce_ms / 1000)
            latest = self._throttle_latest_send.pop(throttle_key, None)
            self._throttle_tasks.pop(throttle_key, None)
            if latest is not None:
                await latest()

        self._throttle_tasks[throttle_key] = asyncio.ensure_future(fire_throttled())

    # --- reservations, jog arming and safety limits (contract v2, block 1) ---------------------------

    async def _access_request(self, method: str, path: str, body: dict | None = None, conditional: tuple[int, str] | None = None) -> AccessResult:
        """One request of the reservation/limits family, answered as an AccessResult: it never raises, and a
        refusal carries the stable code the server gave (other-account, other-controller, controller-id-required,
        jog-not-armed) so the caller can say which."""
        ticket = self.revisions.begin(*conditional) if conditional is not None else None
        try:
            kwargs: dict = {}
            if body is not None:
                kwargs["json"] = {**body, "controllerId": access.get_controller_id()} if method == "POST" else body
            if ticket is not None and ticket.if_match:
                kwargs["headers"] = {"If-Match": ticket.if_match}
            resp = await self._http(method, path, **kwargs)
        except (httpx.HTTPError, OSError) as e:
            if ticket is not None and conditional is not None:
                self.revisions.finish(conditional[0], ticket.seq, None)
            return AccessResult(False, 0, access.failure_code_for(0, None), str(e) or e.__class__.__name__)
        try:
            data = resp.json()
        except ValueError:
            data = None
        if ticket is not None and conditional is not None:
            self.revisions.finish(conditional[0], ticket.seq, access.revision_of(data))
        if resp.status_code < 400:
            expires = data.get("expiresAt") if isinstance(data, dict) else None
            return AccessResult(True, resp.status_code, "", "", float(expires) if isinstance(expires, (int, float)) and not isinstance(expires, bool) else None, data)
        server_code = data.get("code") if isinstance(data, dict) and isinstance(data.get("code"), str) else None
        detail = data.get("error") if isinstance(data, dict) and isinstance(data.get("error"), str) else f"HTTP {resp.status_code}"
        return AccessResult(False, resp.status_code, access.failure_code_for(resp.status_code, server_code), detail, None, data)

    async def claim_robot(
        self, robot_id: int, *, ttl_ms: int | None = None, force: bool = False, reason: str = "", unconditional: bool = False
    ) -> AccessResult:
        """POST /api/robot/:id/claim - reserves the robot for this account and this program. A renewal of one's own
        reservation (`unconditional`) and a take-over (`force`) never carry If-Match."""
        body: dict = {}
        if ttl_ms:
            body["ttlMs"] = ttl_ms
        if force:
            body["force"] = True
        if reason:
            body["reason"] = reason
        conditional = None if (unconditional or force) else (robot_id, "claim")
        return await self._access_request("POST", f"/api/robot/{robot_id}/claim", body, conditional)

    async def release_robot(self, robot_id: int, reason: str = "") -> AccessResult:
        """POST /api/robot/:id/release."""
        return await self._access_request("POST", f"/api/robot/{robot_id}/release", {"reason": reason} if reason else {}, (robot_id, "release"))

    async def arm_jog(self, robot_id: int, armed: bool, ttl_ms: int | None = None) -> AccessResult:
        """POST /api/robot/:id/jog-arm - arms or disarms the jog of one robot (`expires_at` says until when)."""
        body: dict = {"armed": armed}
        if armed and ttl_ms:
            body["ttlMs"] = ttl_ms
        result = await self._access_request("POST", f"/api/robot/{robot_id}/jog-arm", body)
        if result.ok:
            self.jog_armed_until[robot_id] = result.expires_at if armed else None
        return result

    async def set_robot_enabled(self, robot_id: int, enable: bool) -> AccessResult:
        """POST /api/robot/:id/command with `disable` or `enable` - the safe mode of one robot. `disable` stops the
        robot and the server then refuses its other commands (423); `enable` brings it back and is off by default on
        the server (403 enable-not-allowed) and only for an administrator (403 admin-required)."""
        return await self._access_request("POST", f"/api/robot/{robot_id}/command", {"command": "enable" if enable else "disable"})

    async def refresh_access(self, robot_id: int | None = None, *, claims: bool = True) -> bool:
        """Reads GET /api/claims (unless `claims` is False: the server pushes them and the push is fresh) and
        GET /api/safety-limits (with the robot, also until when its jog is armed). A server that predates a route
        keeps what this program already had. Returns False when nothing could be read."""
        got = False
        listed = await self._access_request("GET", "/api/claims") if claims else None
        if listed is not None and listed.ok:
            self.claims = access.parse_claims(listed.body)
            got = True
        path = "/api/safety-limits" if robot_id is None else f"/api/safety-limits?robotId={robot_id}"
        limits = await self._access_request("GET", path)
        if limits.ok:
            self.safety = access.parse_safety_limits(limits.body)
            robot = limits.body.get("robot") if isinstance(limits.body, dict) else None
            until = robot.get("jogArmedUntil") if isinstance(robot, dict) else None
            if robot_id is not None:
                self.jog_armed_until[robot_id] = float(until) if isinstance(until, (int, float)) and not isinstance(until, bool) else None
            got = True
        return got

    async def fetch_robot(self, robot_id: int) -> dict | None:
        """GET /api/robot/:id - one robot with its revision (kept for the next write); None when it could not be
        read or the server predates the route."""
        result = await self._access_request("GET", f"/api/robot/{robot_id}")
        if not result.ok or not isinstance(result.body, dict) or not isinstance(result.body.get("robot"), dict):
            return None
        self.revisions.learn(robot_id, access.revision_of(result.body))
        return result.body["robot"]

    async def refresh_robot(self, robot_id: int) -> bool:
        """Reads one robot again and puts it in the local mirror. Called after a 412: the robot changed under this
        program, and what is shown may be behind."""
        robot = await self.fetch_robot(robot_id)
        if robot is None:
            return False
        for controller in self.state.raw.get("controllers") or []:
            if not isinstance(controller, dict):
                continue
            for existing in controller.get("robots") or []:
                if isinstance(existing, dict) and existing.get("id") == robot_id:
                    existing.update(robot)
                    self._last_payload_json = json.dumps(self.state.raw, sort_keys=True)
                    self.state_changed.emit(self.state)
                    return True
        return False

    async def fetch_audit(self, limit: int | None = None, type: str | None = None, robot_id: int | None = None, verify: bool = False) -> tuple[AccessResult, access.AuditRead | None]:
        """GET /api/audit (administrators only): the newest lines of the audit record, with the verification of the
        server over the whole record when asked."""
        result = await self._access_request("GET", "/api/audit" + access.audit_query(limit, type, robot_id, verify))
        return result, (access.parse_audit(result.body) if result.ok else None)

    async def fetch_audit_jsonl(self, limit: int | None = None, type: str | None = None, robot_id: int | None = None) -> str | None:
        """The lines as the server stores them (?format=jsonl), for saving to a file; None when they could not be read."""
        query = access.audit_query(limit, type, robot_id)
        try:
            resp = await self._http("GET", "/api/audit" + query + ("&" if query else "?") + "format=jsonl")
        except (httpx.HTTPError, OSError):
            return None
        return resp.text if resp.status_code == 200 else None

    async def fetch_submitted_models(self) -> tuple[int, object] | None:
        """GET /api/models: the models the editors submitted to the server (any signed-in account)."""
        return await self._request_json("GET", "/api/models", auth=True)

    async def fetch_model_download(self, category: str, slug: str) -> tuple[int, object] | None:
        """GET /api/models/:category/:slug/download: the URDF and the meshes of one submitted model."""
        return await self._request_json("GET", submitted_models.download_path(category, slug), auth=True)

    async def fetch_users(self) -> AccessResult:
        """GET /api/users (administrators only): the accounts of the server, without their password hashes."""
        return await self._access_request("GET", "/api/users")

    async def create_user(self, username: str, password: str, role: str) -> AccessResult:
        """POST /api/users (administrators only)."""
        return await self._access_request("POST", "/api/users", {"username": username, "password": password, "role": role})

    async def update_user(self, username: str, new_username: str = "", password: str = "", role: str = "") -> AccessResult:
        """PUT /api/users/:username (administrators only): a new name, a new password and/or a new role. Every
        session already open for that account is closed by the server."""
        body: dict = {}
        if new_username.strip():
            body["newUsername"] = new_username.strip()
        if password:
            body["password"] = password
        if role:
            body["role"] = role
        return await self._access_request("PUT", "/api/users/" + urllib.parse.quote(username, safe=""), body)

    async def totp_call(self, method: str, path: str, body: dict | None = None) -> tuple[int, object, str | None]:
        """One request of the second-step family: (status, parsed body, Retry-After). Unlike the other calls it does not
        renew the session and repeat itself on a 401: a wrong password or code is an answer here, and sending it twice would
        count twice against the server's wait. Status 0 means the server could not be reached."""
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with httpx.AsyncClient(headers=HYDRA_CLIENT_HEADERS) as client:
                resp = await client.request(method, f"{self.info.base_url}{path}", headers=headers, json=body, timeout=5.0)
        except (httpx.HTTPError, OSError):
            return 0, None, None
        try:
            data = resp.json()
        except ValueError:
            data = None
        return resp.status_code, data, resp.headers.get("Retry-After")

    async def delete_user(self, username: str) -> AccessResult:
        """DELETE /api/users/:username (administrators only)."""
        return await self._access_request("DELETE", "/api/users/" + urllib.parse.quote(username, safe=""))

    async def reset_user_totp(self, username: str) -> tuple[int, object, str | None]:
        """DELETE /api/users/:username/totp (administrators only): removes the second step of an account that lost both the
        phone and the recovery codes."""
        return await self.totp_call("DELETE", "/api/users/" + urllib.parse.quote(username, safe="") + "/totp")

    def claims_are_pushed(self, within_s: float = 30.0) -> bool:
        """Whether the server pushed the reservations recently, so the poll of GET /api/claims can rest."""
        return self.claims_pushed_at > 0 and time.monotonic() - self.claims_pushed_at < within_s

    async def put_safety_limits(self, patch: dict) -> AccessResult:
        """PUT /api/admin/safety-limits (administrators only); on success the state this connection holds is the one
        the server now has."""
        result = await self._access_request("PUT", "/api/admin/safety-limits", patch)
        if result.ok:
            self.safety = access.parse_safety_limits(result.body)
        return result

    async def stop_all(self) -> StopAllResult:
        """The global STOP: POST /api/stop-all stops every robot of this
        server, whoever reserved it. It goes out at once (no wait for a
        refresh), is retried once when nobody answers, falls back to the
        per-robot `stop` for every known robot when the server rate limits
        (429), and never raises: a stop that nothing confirmed comes back
        as `StopAllResult.not_confirmed(reason)` so the caller can keep a
        visible "not confirmed" state. A confirmed answer also stops the
        robots in the local mirror, so the UI shows it before the next
        broadcast."""
        reason = ""
        for attempt in range(2):
            try:
                resp = await self._http("POST", "/api/stop-all", timeout=STOP_ALL_TIMEOUT_S)
            except (httpx.HTTPError, OSError) as e:
                reason = str(e) or e.__class__.__name__
                if attempt == 0:
                    await asyncio.sleep(STOP_ALL_RETRY_DELAY_S)
                continue
            if resp.status_code in (404, 429):
                # 429: over the server's rate limit. 404: a server that does not
                # have the route yet. Either way the robots are stopped one by one.
                return await self._stop_robots_one_by_one()
            if resp.status_code != 200:
                message = describe_rejection(resp, _("MSG_NET_WHAT_STOP"))
                self.error.emit(message)
                return StopAllResult.not_confirmed(message)
            try:
                body = resp.json()
            except ValueError:
                body = None
            if not isinstance(body, dict):
                return StopAllResult.not_confirmed(_("MSG_NET_NOT_JSON"))
            result = StopAllResult.from_json(body)
            self._apply_stopped(result)
            return result
        self.error.emit(_("MSG_NET_STOP_FAILED", reason=reason))
        return StopAllResult.not_confirmed(reason)

    async def _stop_robots_one_by_one(self) -> StopAllResult:
        """The fallback when the global call is rate limited: the atomic
        `stop` command for every robot this server is known to have."""
        known = [(c.id, r) for c in self.state.controllers for r in c.robots]
        if not known:
            return StopAllResult.not_confirmed("no known robot to stop")
        entries: list[StopAllRobot] = []
        for controller_id, robot in known:
            error: str | None = None
            for attempt in range(2):
                try:
                    resp = await self._http(
                        "POST", f"/api/robot/{robot.id}/command", timeout=STOP_ALL_TIMEOUT_S, json={"command": "stop", "params": {}, **command_sequence.next_for("stop")}
                    )
                    error = None if resp.status_code < 400 else describe_rejection(resp, _("MSG_NET_WHAT_STOP"))
                    break
                except (httpx.HTTPError, OSError) as e:
                    error = str(e) or e.__class__.__name__
                    if attempt == 0:
                        await asyncio.sleep(STOP_ALL_RETRY_DELAY_S)
            try:
                numeric_id = int(robot.id)
            except ValueError:
                numeric_id = 0
            entries.append(
                StopAllRobot(
                    robot_id=numeric_id, controller_id=controller_id, name=str(robot.raw.get("name") or ""),
                    stopped=error is None, error=error,
                )
            )
        failed = sum(1 for e in entries if not e.stopped)
        result = StopAllResult(
            success=failed == 0, stopped_count=len(entries) - failed, failed_count=failed,
            persisted=True, robots=entries, via_fallback=True,
        )
        self._apply_stopped(result)
        return result

    def _apply_stopped(self, result: StopAllResult) -> None:
        """Mirrors a confirmed stop into the local state (the next broadcast confirms or corrects it)."""
        stopped_ids = {str(r.robot_id) for r in result.robots if r.stopped}
        touched = False
        for controller in self.state.controllers:
            for robot in controller.robots:
                if robot.id in stopped_ids:
                    robot.stop_playing()
                    touched = True
        if touched:
            self.state_changed.emit(self.state)

    @staticmethod
    def _command_warnings(resp: "httpx.Response") -> str:
        try:
            body = resp.json()
        except ValueError:
            return ""
        items = body.get("warnings") if isinstance(body, dict) else None
        if not isinstance(items, list):
            return ""
        return "; ".join(str(w.get("message", w)) if isinstance(w, dict) else str(w) for w in items)

    async def fetch_system_metrics(self) -> dict | None:
        """GET /api/system/metrics - no auth required server-side. Returns
        None on any network error rather than raising, since this is a
        best-effort background poll, not a critical read."""
        try:
            resp = await self._http("GET", "/api/system/metrics")
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
            self.error.emit(_("MSG_NET_FETCH_FAILED", error=e))
            # Still try the WebSocket below - a server that's up but whose
            # REST fetch raced a restart shouldn't be given up on immediately.

        self._recv_task = asyncio.ensure_future(self._run())
        self._metrics_task = asyncio.ensure_future(self._metrics_loop())

    async def _run(self) -> None:
        while not self._closing:
            if self._token is None and not await self._renew_session(None):
                # No point opening a WS the server will reject with code 1008 -
                # wait and retry the login itself instead of spinning a
                # connect/reject loop against a server that's simply not up yet.
                # Honors the server's own rate-limit retryAfterMs when THAT
                # was the reason login failed (see login()'s own comment) -
                # otherwise a wrong password or brief server restart would
                # keep retrying every RECONNECT_DELAY_S straight into a real
                # 15-minute lockout instead of just backing off once.
                self.status_changed.emit("disconnected")
                if self._login_rejected:
                    # Wrong or missing credentials: retrying only spends the
                    # server's login attempts. Editing them reconnects.
                    return
                await asyncio.sleep(self._login_retry_after_s or RECONNECT_DELAY_S)
                continue
            connected_once = False
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
                # (now a finite 128 MB ceiling: far above any real tree, but a
                # hostile or broken server can no longer exhaust the PC's memory)
                async with self._open_ws() as ws:
                    self._ws = ws
                    connected_once = True
                    self.status_changed.emit("connected")
                    async for raw in ws:
                        self._handle_message(raw)
            except (websockets.WebSocketException, OSError) as e:
                logger.info("HydraConnection %s: WebSocket dropped (%s)", self.info.host, e)
                # A rejected/expired token surfaces as a closed connection here,
                # not an exception with a status code - force a fresh login on
                # the next loop iteration rather than retrying the same
                # (possibly now-invalid) token forever.
                rejected = isinstance(e, websockets.InvalidHandshake) or (
                    isinstance(e, websockets.ConnectionClosed) and e.rcvd is not None and e.rcvd.code == 1008
                )
                if rejected:
                    # The server refused this token (expired, revoked): the
                    # next pass renews it (refresh token first, then login).
                    self._token = None
                # Anything else (server down, link dropped) keeps the session:
                # logging in again on every blip would spend the server's
                # login limit.
            finally:
                self._ws = None
            if self._closing:
                break
            self.status_changed.emit("disconnected")
            await asyncio.sleep(RECONNECT_DELAY_S)

    def _open_ws(self):
        token = self._token
        return websockets.connect(
            self.info.ws_url(),
            subprotocols=self.info.ws_subprotocols(token),
            open_timeout=5.0,
            max_size=WS_MAX_MESSAGE_BYTES,
        )

    def _handle_message(self, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
        except ValueError:
            logger.warning("HydraConnection %s: malformed WS message", self.info.host)
            return
        if not isinstance(msg, dict):
            return
        if msg.get("error"):
            # The server refused something this client sent (a settings write
            # from a non-admin session, for one). The local mirror may now
            # show a value the server never applied: say so and re-read.
            logger.warning("HydraConnection %s: %s", self.info.host, msg["error"])
            self.error.emit(_("MSG_NET_WRITE_REJECTED_SERVER", error=msg["error"]))
            self._last_payload_json = None
            self._resync_after_error()
            return
        # A real targeted delta (server.ts's own broadcastRobotDelta(),
        # sent only to a connection that declared schema 2 - see
        # ServerInfo.ws_url()'s own comment) - handled separately from the
        # full-tree branch below, which stays exactly as it was for a
        # schema-1 "delta"/"settings" message.
        if msg.get("type") == "delta" and msg.get("schema") == 2 and "robotId" in msg:
            self._apply_robot_delta(msg)
            return
        # Who reserves which robot, pushed when a reservation, an arming or a stop changes (only to a connection that
        # asked for remoteApiVersion=2): the same list as GET /api/claims, so the poll need not run.
        if msg.get("type") == "claims":
            self.claims = access.parse_claims(msg)
            self.claims_pushed_at = time.monotonic()
            for claim in self.claims:
                if claim.controller_id == access.get_controller_id():
                    self.jog_armed_until[claim.robot_id] = claim.jog_armed_until
            self.claims_changed.emit()
            return
        # One progress line of a CAN flash cycle, relayed by the server to admin sessions only: kept as the latest
        # line and announced, so a flasher view can show the live phase and percentage while the request is pending.
        if msg.get("type") == "canota_progress":
            payload = msg.get("payload")
            if isinstance(payload, dict):
                self.last_canota_progress = payload
                self.canota_progress.emit(payload)
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
        if not is_settings_tree(payload):
            logger.warning("HydraConnection %s: ignored a settings message that is not a settings tree", self.info.host)
            return
        payload_json = json.dumps(payload, sort_keys=True)
        if payload_json == self._last_payload_json:
            return  # our own echoed-back write - see push_state()'s own comment
        self._last_payload_json = payload_json
        self.state = HydraState(payload)
        self.state_changed.emit(self.state)

    def _resync_after_error(self) -> None:
        async def _reload() -> None:
            try:
                await self.fetch_state()
            except (httpx.HTTPError, ValueError) as e:
                logger.info("HydraConnection %s: resync failed (%s)", self.info.host, e)

        asyncio.ensure_future(_reload())

    def _apply_robot_delta(self, msg: dict) -> None:
        """Applies one {controllerId, robotId, patch, cameraId?, cameraPatch?}
        delta in place onto self.state's own raw dict (HydraState wraps a
        mutable dict - see models.py's own header comment, every RobotView/
        CameraView already mutates through to the same underlying object).

        Validates the robot exists locally BEFORE touching anything: if it
        doesn't (this mirror is stale, or somehow missed the robot's own
        initial full-tree load), the delta is discarded and a full
        fetch_state() is forced instead of ever creating a "ghost" robot
        from a partial patch - non-optional.

        DOES recompute _last_payload_json from the now-mutated state
        once the patch is applied (see the assignment below its own
        comment for the real bug this fixes) - this delta's own small
        payload is still never compared against that guard directly, but
        leaving the guard's baseline stale after a real state mutation is
        exactly what let a later legitimate full snapshot get silently
        mistaken for our own echo and dropped."""
        controller_id = msg.get("controllerId")
        robot_id = msg.get("robotId")
        patch = msg.get("patch")
        if not isinstance(controller_id, str) or not isinstance(patch, dict):
            return
        target_robot: dict | None = None
        target_camera: dict | None = None
        for c in self.state.raw.get("controllers") or []:
            if not isinstance(c, dict) or str(c.get("id", "")) != controller_id:
                continue
            for r in c.get("robots") or []:
                if isinstance(r, dict) and r.get("id") == robot_id:
                    target_robot = r
                    break
            camera_id = msg.get("cameraId")
            if camera_id is not None:
                for cam in c.get("cameras") or []:
                    if isinstance(cam, dict) and cam.get("id") == camera_id:
                        target_camera = cam
                        break
            break
        if target_robot is None:
            logger.info("HydraConnection %s: delta for unknown robot %r - forcing full reload", self.info.host, robot_id)
            self._resync_after_error()
            return
        target_robot.update(patch)
        camera_patch = msg.get("cameraPatch")
        if target_camera is not None and isinstance(camera_patch, dict):
            target_camera.update(camera_patch)
        # this used to leave _last_payload_json completely untouched
        # (see this method's own docstring, which was right that a delta's
        # OWN small payload is never compared against it - but wrong that
        # nothing here needs to touch it at all). Real bug: settings #1 ->
        # this delta -> settings #2 that happens to be byte-for-byte
        # identical to settings #1 (e.g. the delta's own change gets
        # reverted/superseded server-side and the full tree converges back)
        # - _last_payload_json was still settings #1's own JSON, so
        # settings #2 matched it and was WRONGLY treated as "our own
        # echoed-back write" and silently dropped at the top of
        # _on_ws_message(), leaving self.state permanently stuck on the
        # post-delta value the server had already moved past. Recomputing
        # here to match the ACTUAL current (now delta-mutated) state means
        # settings #2's JSON - which no longer matches this recomputed
        # value, since the delta really did change something - correctly
        # fails the echo check and gets applied for real.
        self._last_payload_json = json.dumps(self.state.raw, sort_keys=True)
        self.state_changed.emit(self.state)

    async def disconnect(self) -> None:
        self._closing = True
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception as error:  # a socket that is already gone must not block the rest of the cleanup
                logger.info("HydraConnection %s: closing the socket failed (%s)", self.info.host, error)
        if self._recv_task is not None:
            self._recv_task.cancel()
        if self._metrics_task is not None:
            self._metrics_task.cancel()
        for task in self._throttle_tasks.values():
            task.cancel()
        self._throttle_tasks.clear()
        self._throttle_latest_send.clear()
        self.status_changed.emit("disconnected")
