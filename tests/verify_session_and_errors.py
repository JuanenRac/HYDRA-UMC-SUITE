# =============================================================================
# HYDRA-UMC SUITE - tests/verify_session_and_errors.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies, against a small real HTTP + WebSocket server on localhost (no
# robot, no real HYDRA-UMC-SERVER), how net/client.py's HydraConnection
# behaves around the session and the server's refusals:
#   - a server found by the scan (no credentials) is never sent a login
#   - a rejected login (401) is not retried by the reconnect loop
#   - an expired access token (403 TOKEN_EXPIRED) is renewed through
#     /api/refresh and the request repeated once
#   - a 400 / 409 / role-403 answer to a command reads differently, and a
#     200 that carries warnings counts as "not applied" (rolled back)
#   - the WebSocket sends the token as the "hydra.bearer" subprotocol (never
#     in the address); a server that only reads ?token= is never given it
#   - an error message pushed over the WebSocket is reported and re-read
#   - an answer that is cut in the middle fails the read with a network error and the next read works
#   - a server that is off, then comes up, then drops the connection and comes back: the reconnect loop keeps the
#     session, never logs in again, ignores garbage and shows the state of the connection that survives
#   - the version tag "1.2.0" gives bootloader version 1.2 (not 1.0)
# =============================================================================
import asyncio
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

import httpx
import websockets
from websockets.asyncio.server import serve

from hydra_suite.can_ota import parse_version_tag
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net import client as client_module
from hydra_suite.net.client import HydraConnection

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class Behaviour:
    """What the fake server answers; the handler reads it on every request."""

    login_status = 200
    command_status = 200
    command_body: dict = {"success": True}
    expired_tokens: set[str] = set()
    logins = 0
    refreshes = 0
    last_command_auth = ""
    cut_settings = 0  # answers to GET /api/settings that are cut in the middle of the body, then normal


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        if auth.removeprefix("Bearer ") in Behaviour.expired_tokens:
            return self._send(403, {"error": "expired", "code": "TOKEN_EXPIRED"})
        if self.path == "/api/settings":
            if Behaviour.cut_settings > 0:
                Behaviour.cut_settings -= 1
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", "1000")
                self.end_headers()
                self.wfile.write(b'{"controllers":')
                self.close_connection = True
                return
            return self._send(200, {"controllers": [], "activeControllerId": ""})
        self._send(404, {})

    def do_POST(self):
        body = self._body()
        if self.path == "/api/login":
            Behaviour.logins += 1
            if Behaviour.login_status != 200:
                return self._send(Behaviour.login_status, {"error": "Invalid credentials"})
            return self._send(200, {"success": True, "token": f"jwt-{Behaviour.logins}", "refreshToken": "r-1", "role": "admin"})
        if self.path == "/api/refresh":
            Behaviour.refreshes += 1
            return self._send(200, {"success": True, "token": "jwt-fresh", "refreshToken": "r-2", "role": "admin"})
        if self.path.endswith("/command"):
            auth = self.headers.get("Authorization", "")
            Behaviour.last_command_auth = auth
            if auth.removeprefix("Bearer ") in Behaviour.expired_tokens:
                return self._send(403, {"error": "expired", "code": "TOKEN_EXPIRED"})
            return self._send(Behaviour.command_status, Behaviour.command_body)
        self._send(404, {})


async def wait_for_key(seen, key, timeout=5.0):
    """Waits until the fake server has recorded `key` (a fixed sleep made the
    check fail on a loaded machine)."""
    waited = 0.0
    while not seen.get(key) and waited < timeout:
        await asyncio.sleep(0.05)
        waited += 0.05


def start_http():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def make_conn(port, **kwargs):
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=port, **kwargs))
    conn.errors = []
    conn.error.connect(conn.errors.append)
    return conn


async def run():
    http_server = start_http()
    port = http_server.server_address[1]

    # --- a scan result has no credentials: nothing is sent ----------------
    conn = make_conn(port)
    check("no credentials: login() returns False", await conn.login(), False)
    check("no credentials: not a single login request reached the server", Behaviour.logins, 0)
    check("no credentials: the reconnect loop must wait for the operator", conn._login_rejected, True)

    # --- a rejected login is not retried ----------------------------------
    Behaviour.login_status = 401
    conn = make_conn(port, username="a", password="wrong")
    await conn.login()
    check("401 login: marked as rejected", conn._login_rejected, True)
    before = Behaviour.logins
    await asyncio.wait_for(conn._run(), timeout=2.0)  # returns instead of looping
    check("401 login: _run() makes no second attempt loop", Behaviour.logins - before, 1)
    Behaviour.login_status = 200

    # --- expired token: refresh + one retry --------------------------------
    conn = make_conn(port, username="a", password="b")
    await conn.login()
    check("login stores the first token", conn._token, f"jwt-{Behaviour.logins}")
    Behaviour.expired_tokens = {conn._token}
    logins_before = Behaviour.logins
    await conn.send_command(1, "stop")
    check("expired token: renewed through /api/refresh", Behaviour.refreshes, 1)
    check("expired token: no new login was needed", Behaviour.logins, logins_before)
    check("expired token: the retry carried the fresh token", Behaviour.last_command_auth, "Bearer jwt-fresh")
    check("expired token: no error shown", conn.errors, [])
    Behaviour.expired_tokens = set()

    # --- the refusals read differently ------------------------------------
    Behaviour.command_status, Behaviour.command_body = 400, {"error": "unknown command"}
    conn.errors.clear()
    await conn.send_command(1, "enable")
    check("400 unknown command: the server's reason is shown", any("unknown command" in e for e in conn.errors), True)

    Behaviour.command_status, Behaviour.command_body = 409, {"error": "robot reserved by alice"}
    conn.errors.clear()
    await conn.send_command(1, "jog")
    check("409: says the robot is reserved by another account", any("reserved by another account" in e for e in conn.errors), True)

    Behaviour.command_status, Behaviour.command_body = 403, {"error": "Access denied: admin privileges required"}
    conn.errors.clear()
    await conn.send_command(1, "jog")
    check("role 403: reads as a missing permission, not an expired session", any("permission denied" in e for e in conn.errors), True)

    # --- 200 with warnings = nothing applied -> rollback -------------------
    Behaviour.command_status = 200
    Behaviour.command_body = {"success": True, "warnings": [{"message": "speed out of range - not applied"}]}
    conn.state = HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [{"id": "c1", "robots": [{"id": 1, "speed": 100}], "cameras": []}],
        }
    )
    conn.errors.clear()
    await conn.send_command(1, "speed", {"speed": 5}, local_mutate=lambda r: r.raw.update({"speed": 5}))
    check("warnings: reported", any("not applied" in e for e in conn.errors), True)
    check("warnings: the local value is rolled back", conn.state.raw["controllers"][0]["robots"][0]["speed"], 100)

    # --- a pushed error message is reported and re-read --------------------
    conn.errors.clear()
    conn._handle_message(json.dumps({"error": "Access denied: admin privileges required"}))
    await asyncio.sleep(0.2)
    check("WS error message: shown to the operator", any("Access denied" in e for e in conn.errors), True)
    check("WS error message: the local copy was re-read", conn.state.raw.get("controllers"), [])

    # --- an answer cut in the middle of its body: the read fails with a network error, the next one works -----
    Behaviour.cut_settings = 1
    conn = make_conn(port, username="a", password="b")
    try:
        await conn.fetch_state()
        outcome = "read"
    except httpx.HTTPError:
        outcome = "network error"
    check("cut answer: the read fails with a network error", outcome, "network error")
    again = await conn.fetch_state()
    check("cut answer: the next read gives the state", again.raw.get("activeControllerId"), "")

    http_server.shutdown()

    # --- WebSocket: the token travels as a subprotocol and never in the address -----
    seen = {"modern": None, "old": None}

    async def modern(ws):
        seen["modern"] = (ws.request.path, ws.subprotocol)
        await ws.send(json.dumps({"type": "settings", "payload": {"controllers": [], "activeControllerId": "x"}}))
        await asyncio.sleep(0.3)

    async def old(ws):
        seen["old"] = ws.request.path
        await ws.send(json.dumps({"type": "settings", "payload": {"controllers": [], "activeControllerId": "y"}}))
        await asyncio.sleep(0.3)

    def old_process_request(connection, request):
        # A server from before the subprotocol: it only accepts ?token=, which this client no longer sends
        if "token=" not in request.path:
            return connection.respond(401, "token required\n")
        return None

    async with serve(modern, "127.0.0.1", 0, subprotocols=["hydra.bearer"]) as modern_server:
        modern_port = modern_server.sockets[0].getsockname()[1]
        conn = make_conn(modern_port, username="a", password="b")
        conn._token = "tok.en-1"
        task = asyncio.ensure_future(conn._run())
        await wait_for_key(seen, "modern")
        conn._closing = True
        task.cancel()
        path, chosen = seen["modern"]
        check("WS: the token is not in the address", "token" in path, False)
        check("WS: the server answered the hydra.bearer subprotocol", chosen, "hydra.bearer")

    async with serve(old, "127.0.0.1", 0, process_request=old_process_request) as old_server:
        old_port = old_server.sockets[0].getsockname()[1]
        conn = make_conn(old_port, username="a", password="b")
        conn._token = "tok.en-2"
        task = asyncio.ensure_future(conn._run())
        await asyncio.sleep(1.5)
        conn._closing = True
        task.cancel()
        check("WS: a server that only reads ?token= is never given the token in the address", seen["old"], None)

    # --- the server is off, comes up, drops the connection and comes back -----------------------------------------
    client_module.RECONNECT_DELAY_S = 0.1
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    flaky_port = probe.getsockname()[1]
    probe.close()  # a port that nobody listens on yet
    life = {"connections": 0, "subprotocols": []}

    def settings_message(label):
        return json.dumps({"type": "settings", "payload": {"controllers": [], "activeControllerId": label}})

    async def flaky(ws):
        life["connections"] += 1
        life["subprotocols"].append(ws.subprotocol)
        if life["connections"] == 1:
            await ws.send(settings_message("before-the-drop"))
            await asyncio.sleep(0.15)
            await ws.close(code=1011)  # the server goes away in the middle of the session
            return
        await ws.send("this is not json")
        await ws.send(json.dumps([1, 2, 3]))
        await ws.send(settings_message("after-the-drop"))
        await asyncio.sleep(1.0)

    statuses = []
    logins_before_drop = Behaviour.logins
    conn = make_conn(flaky_port, username="a", password="b")
    conn.status_changed.connect(statuses.append)
    conn._token = "tok.en-3"
    task = asyncio.ensure_future(conn._run())
    waited = 0.0
    while "disconnected" not in statuses and waited < 8.0:  # a refused connection is slow to be told on some systems
        await asyncio.sleep(0.05)
        waited += 0.05
    check("server off: the client says it is disconnected and keeps trying", ("disconnected" in statuses, "connected" in statuses), (True, False))
    async with serve(flaky, "127.0.0.1", flaky_port, subprotocols=["hydra.bearer"]):
        waited = 0.0
        while conn.state.raw.get("activeControllerId") != "after-the-drop" and waited < 8.0:
            await asyncio.sleep(0.05)
            waited += 0.05
        conn._closing = True
        task.cancel()
    check("link drop: the client came back by itself and shows the state of the second connection", conn.state.raw.get("activeControllerId"), "after-the-drop")
    check("link drop: it connected twice", life["connections"], 2)
    check("link drop: both connections carried the token as the subprotocol", life["subprotocols"], ["hydra.bearer", "hydra.bearer"])
    check("link drop: it connected, dropped and connected again", [s for s in statuses if s in ("connected", "disconnected")][-3:], ["connected", "disconnected", "connected"])
    check("link drop: the session was kept and no new login was made", (conn._token, Behaviour.logins), ("tok.en-3", logins_before_drop))
    client_module.RECONNECT_DELAY_S = 3.0

    # --- the bootloader version -------------------------------------------
    check("version tag 1.2.0 -> (1, 2)", parse_version_tag("1.2.0"), (1, 2))
    check("version tag v3.10 -> (3, 10)", parse_version_tag("v3.10"), (3, 10))
    check("no tag -> (0, 0)", parse_version_tag(None), (0, 0))
    check("garbage -> (0, 0)", parse_version_tag("abc"), (0, 0))


asyncio.run(run())
assert client_module.WS_MAX_MESSAGE_BYTES > 1024 * 1024 * 16
if failures:
    print(f"{failures} check(s) failed")
    sys.exit(1)
print("verify_session_and_errors: PASS")
