# =============================================================================
# HYDRA-UMC SUITE - tests/verify_hostile_server_answers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies, against a small real HTTP server on localhost (no robot, no real
# HYDRA-UMC-SERVER), how net/client.py's HydraConnection reads answers that are
# wrong, partial or hostile:
#   - the global STOP never raises, whatever a 200 answer carries (a robot id
#     that is not a number, a robots list that is not a list, ...), and shows
#     such an answer as not clean
#   - a server without the /api/stop-all route (404) gets the same per-robot
#     stop that a rate limited one (429) does, and a server with no known robot
#     leaves the STOP "not confirmed"
#   - a WebSocket message of the wrong shape (bytes, a list, a settings tree
#     whose controllers are not objects, a delta for a robot that does not
#     exist) never raises and never replaces the state with a broken tree
#   - the settings read refuses a body that is not a settings tree
#   - the messages for refused writes read differently for 400 / 401 / 403 /
#     409 / 5xx, also when the body is not JSON
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

import httpx
import qasync
from PySide6.QtWidgets import QApplication

from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net import client as client_module
from hydra_suite.net.client import HydraConnection, StopAllResult, describe_rejection

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class Behaviour:
    stop_all_status = 200
    stop_all_body: bytes = b"{}"
    settings_body: bytes = b"{}"
    settings_reads = 0
    command_requests: list = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _answer(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/api/settings":
            Behaviour.settings_reads += 1
            self._answer(200, Behaviour.settings_body)
        else:
            self._answer(404, b"{}")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if self.path == "/api/stop-all":
            self._answer(Behaviour.stop_all_status, Behaviour.stop_all_body)
        elif self.path.endswith("/command"):
            Behaviour.command_requests.append((self.path, json.loads(raw or b"{}")))
            self._answer(200, b"{}")
        else:
            self._answer(404, b"{}")


def start_http():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def make_conn(port, robots=2):
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=port))
    conn._token = "tok"
    conn.state = HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [
                {
                    "id": "c1",
                    "robots": [
                        {"id": n, "name": f"R{n}", "playbackState": {"isPlaying": True}} for n in range(1, robots + 1)
                    ],
                }
            ],
        }
    )
    return conn


def reset(status=200, body=b"{}", settings=b"{}"):
    Behaviour.stop_all_status = status
    Behaviour.stop_all_body = body
    Behaviour.settings_body = settings
    Behaviour.settings_reads = 0
    Behaviour.command_requests = []


def playing(conn):
    return [r.is_playing for r in conn.state.controllers[0].robots]


HOSTILE_STOP_BODIES = [
    {"robots": [{"robotId": "abc"}]},
    {"robots": [{"robotId": [1]}]},
    {"robots": [{"robotId": {"a": 1}}]},
    {"robots": [{"robotId": float("nan")}]},
    {"robots": [{"robotId": 1e999}]},
    {"robots": 5},
    {"robots": "text"},
    {"robots": {"a": 1}},
    {"robots": [5, None, "x", []]},
    {"failedCount": "x", "stoppedCount": None, "success": "yes"},
    {"robots": [{"robotId": 1, "stopped": "yes", "reservedBy": 5, "error": ["x"], "name": None, "controllerId": 7}]},
]


async def check_stop_all(port):
    client_module.STOP_ALL_RETRY_DELAY_S = 0.05

    for body in HOSTILE_STOP_BODIES:
        reset(body=json.dumps(body).encode())
        conn = make_conn(port)
        try:
            result = await conn.stop_all()
            raised = False
        except Exception as error:  # the STOP must never raise
            raised = True
            print(f"     raised {error.__class__.__name__}: {error}")
        check(f"stop 200 {json.dumps(body)[:60]}: does not raise", raised, False)
        if not raised:
            check(f"stop 200 {json.dumps(body)[:60]}: is not shown as clean", result.is_clean, False)

    for status in (404, 429):
        reset(status=status, body=b'{"error":"x"}')
        conn = make_conn(port)
        result = await conn.stop_all()
        sent = sorted(p for p, _b in Behaviour.command_requests)
        check(f"{status}: every known robot is stopped one by one", sent, ["/api/robot/1/command", "/api/robot/2/command"])
        check(f"{status}: with the stop command", {b["command"] for _p, b in Behaviour.command_requests}, {"stop"})
        check(f"{status}: flagged as sent one by one", result.via_fallback, True)
        check(f"{status}: the local mirror shows both robots stopped", playing(conn), [False, False])

    reset(status=404, body=b"<html>not found</html>")
    conn = make_conn(port, robots=0)
    result = await conn.stop_all()
    check("404 with no known robot: not confirmed", result.confirmed, False)

    reset(status=200, body=b"<html>captive portal</html>")
    conn = make_conn(port)
    result = await conn.stop_all()
    check("200 that is not JSON: not confirmed", result.confirmed, False)
    check("200 that is not JSON: nothing shown as stopped", playing(conn), [True, True])

    reset(status=200, body=b"[]")
    conn = make_conn(port)
    result = await conn.stop_all()
    check("200 JSON list: not confirmed", result.confirmed, False)

    for status in (400, 401, 403, 409, 500, 502):
        reset(status=status, body=b"<html>no</html>")
        conn = make_conn(port)
        errors = []
        conn.error.connect(errors.append)
        result = await conn.stop_all()
        check(f"{status}: not confirmed, never retried one by one", (result.confirmed, Behaviour.command_requests), (False, []))
        check(f"{status}: the error is announced", len(errors), 1)


def parse_checks():
    for body in HOSTILE_STOP_BODIES:
        try:
            result = StopAllResult.from_json(body)
            check(f"from_json {json.dumps(body)[:60]}: is not clean", result.is_clean, False)
        except Exception as error:
            check(f"from_json {json.dumps(body)[:60]}: does not raise ({error.__class__.__name__})", False, True)
    check("from_json: a numeric text id is read", StopAllResult.from_json({"robots": [{"robotId": "7"}]}).robots[0].robot_id, 7)
    check("from_json: an unreadable id becomes 0", StopAllResult.from_json({"robots": [{"robotId": "abc"}]}).robots[0].robot_id, 0)
    check("from_json: a robot that is not stopped counts as failed", StopAllResult.from_json({"robots": [{"robotId": 1}]}).failed_count, 1)
    check(
        "from_json: counts of the server win over the list",
        StopAllResult.from_json({"failedCount": 3, "stoppedCount": 4, "robots": []}).failed_count,
        3,
    )


def rejection_checks():
    def response(status, content):
        return httpx.Response(status, content=content)

    cases = [
        (400, b'{"error":"unknown command"}', "STOP rejected: unknown command"),
        (400, b"<html>", "STOP rejected: HTTP 400"),
        (400, b"[]", "STOP rejected: HTTP 400"),
        (400, b'{"error":5}', "STOP rejected: HTTP 400"),
        (401, b"{}", "STOP rejected: not authenticated (session expired)"),
        (401, b"<html>", "STOP rejected: not authenticated (session expired)"),
        (403, b'{"code":"TOKEN_EXPIRED"}', "STOP rejected: not authenticated (session expired)"),
        (403, b'{"error":"Access denied"}', "STOP rejected: permission denied (Access denied)"),
        (403, b"<html>", "STOP rejected: permission denied (HTTP 403)"),
        (409, b'{"error":"reserved by alice"}', "STOP rejected: the robot is reserved by another account (reserved by alice)"),
        (500, b"boom", "STOP failed: HTTP 500"),
        (502, b"", "STOP failed: HTTP 502"),
        (404, b"{}", "STOP failed: HTTP 404"),
    ]
    for status, content, expected in cases:
        check(f"describe_rejection {status} {content[:20]!r}", describe_rejection(response(status, content), "STOP"), expected)


async def check_messages(port):
    def fresh():
        conn = make_conn(port)
        events = []
        errors = []
        conn.state_changed.connect(lambda state: events.append(state))
        conn.error.connect(errors.append)
        return conn, events, errors

    unchanged = [
        b"\xff\xfe",
        b"",
        "not json",
        "[]",
        "5",
        "null",
        '"text"',
        '{"type":"other"}',
        '{"type":"settings"}',
        '{"type":"settings","payload":[]}',
        '{"type":"settings","payload":"x"}',
        '{"type":"settings","payload":{"controllers":"x"}}',
        '{"type":"settings","payload":{"controllers":[5]}}',
        '{"type":"settings","payload":{"controllers":[{"id":"c1","robots":"x"}]}}',
        '{"type":"settings","payload":{"controllers":[{"id":"c1","robots":[7]}]}}',
        '{"type":"delta","payload":{"controllers":[null]}}',
        '{"type":"delta","schema":2,"robotId":1,"controllerId":5,"patch":{}}',
        '{"type":"delta","schema":2,"robotId":1,"controllerId":"c1","patch":[]}',
        '{"type":"delta","schema":2,"robotId":1,"controllerId":"c1"}',
    ]
    for message in unchanged:
        conn, events, _errors = fresh()
        before = json.dumps(conn.state.raw, sort_keys=True)
        try:
            conn._handle_message(message)
            raised = False
        except Exception as error:
            raised = True
            print(f"     raised {error.__class__.__name__}: {error}")
        await asyncio.sleep(0.02)  # a forced re-read may be scheduled
        label = repr(message)[:70]
        check(f"message {label}: does not raise", raised, False)
        check(f"message {label}: the state is not replaced by a broken one", json.dumps(conn.state.raw, sort_keys=True), before)
        check(f"message {label}: nothing is announced as a new state", len(events), 0)

    # a delta for a robot this mirror does not know is dropped and the whole tree is read again
    for message in (
        '{"type":"delta","schema":2,"robotId":99,"controllerId":"c1","patch":{"x":1}}',
        '{"type":"delta","schema":2,"robotId":99,"controllerId":"nope","patch":{"x":1}}',
    ):
        conn, events, _errors = fresh()
        reset(settings=json.dumps(conn.state.raw).encode())
        before = json.dumps(conn.state.raw, sort_keys=True)
        conn._handle_message(message)
        await asyncio.sleep(0.4)
        check(f"unknown robot {message[-40:]}: the state is not patched", json.dumps(conn.state.raw, sort_keys=True), before)
        check(f"unknown robot {message[-40:]}: the tree is read again once", Behaviour.settings_reads, 1)

    # a controller list that holds something that is not an object, inside a delta
    conn, events, _errors = fresh()
    conn.state.raw["controllers"].insert(0, "garbage")
    try:
        conn._handle_message('{"type":"delta","schema":2,"robotId":1,"controllerId":"c1","patch":{"name":"X"}}')
        raised = False
    except Exception:
        raised = True
    check("delta over a state with a garbage controller: does not raise", raised, False)

    # an error pushed by the server is announced and reported once
    conn, events, errors = fresh()
    conn._handle_message('{"error":"Access denied"}')
    check("server error: announced", errors, ["Write rejected by the server: Access denied"])
    conn._handle_message('{"error":{"a":1}}')
    check("server error that is not text: announced", len(errors), 2)
    reset(settings=json.dumps(conn.state.raw).encode())
    await asyncio.sleep(0.4)

    # well-formed messages are still applied
    conn, events, _errors = fresh()
    conn._handle_message(
        json.dumps({"type": "settings", "payload": {"controllers": [{"id": "c9", "robots": [{"id": 4, "name": "New"}]}], "activeControllerId": "c9"}})
    )
    check("settings: a well-formed tree is applied", [c.id for c in conn.state.controllers], ["c9"])
    check("settings: and announced once", len(events), 1)
    conn._handle_message(
        json.dumps({"type": "settings", "payload": {"controllers": [{"id": "c9", "robots": [{"id": 4, "name": "New"}]}], "activeControllerId": "c9"}})
    )
    check("settings: the same tree again is taken for our own echo", len(events), 1)
    conn._handle_message(json.dumps({"type": "delta", "schema": 2, "robotId": 4, "controllerId": "c9", "patch": {"name": "Renamed"}}))
    check("delta: a known robot is patched", conn.state.controllers[0].robots[0].raw["name"], "Renamed")
    check("delta: and announced", len(events), 2)
    conn._handle_message(json.dumps({"type": "settings", "payload": {"settings": {}, "controllers": []}}))
    check("settings: an empty controller list is a valid tree", conn.state.controllers, [])
    conn._handle_message(json.dumps({"type": "settings", "payload": {"settings": {}}}))
    check("settings: a tree without controllers is a valid tree", len(events), 4)
    await asyncio.sleep(0.4)  # let the re-reads started above finish before the loop moves on


async def check_fetch_state(port):
    for body in (b"[]", b"null", b'"text"', b"5", b"<html>", b'{"controllers":"x"}', b'{"controllers":[5]}'):
        reset(settings=body)
        conn = make_conn(port)
        before = json.dumps(conn.state.raw, sort_keys=True)
        try:
            await conn.fetch_state()
            outcome = "accepted"
        except ValueError:
            outcome = "refused"
        except Exception as error:
            outcome = f"raised {error.__class__.__name__}"
        check(f"fetch_state {body[:30]!r}: refused", outcome, "refused")
        check(f"fetch_state {body[:30]!r}: the state is kept", json.dumps(conn.state.raw, sort_keys=True), before)

    reset(settings=b'{"settings":{},"controllers":[{"id":"c1","robots":[{"id":3}]}],"activeControllerId":"c1"}')
    conn = make_conn(port)
    state = await conn.fetch_state()
    check("fetch_state: a good tree is read", [r.id for r in state.controllers[0].robots], ["3"])


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    port = start_http().server_address[1]

    parse_checks()
    rejection_checks()
    loop.run_until_complete(check_stop_all(port))
    loop.run_until_complete(check_messages(port))
    loop.run_until_complete(check_fetch_state(port))

    if failures:
        print(f"{failures} check(s) failed")
        sys.exit(1)
    print("verify_hostile_server_answers: PASS")


main()
