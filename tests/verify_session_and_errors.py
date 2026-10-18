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
#     in the address) and falls back to ?token= for a server without it
#   - an error message pushed over the WebSocket is reported and re-read
#   - the version tag "1.2.0" gives bootloader version 1.2 (not 1.0)
# =============================================================================
import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

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

    http_server.shutdown()

    # --- WebSocket: subprotocol first, ?token= for an older server ---------
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
        # A server from before the subprotocol: it only accepts ?token=
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
        await wait_for_key(seen, "old")
        conn._closing = True
        task.cancel()
        check("WS fallback: an older server gets ?token=", bool(seen["old"]) and "token=tok.en-2" in seen["old"], True)

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
