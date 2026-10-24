# =============================================================================
# HYDRA-UMC SUITE - tests/verify_access_network.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies, against a small real HTTP server on localhost (no robot, no real HYDRA-UMC-SERVER):
#   - every robot command, claim, release and jog arming carries the controller id of this program
#   - the refusals (other account, other controller, controller id required, jog not armed) are told apart in
#     the message the operator gets
#   - a robot in Sim never sends a command that moves it (no request at all), STOP still goes out
#   - a jog above the limit of its model is not sent, one inside the limit is
#   - the reservations and the limits are read from the server, and an administrator saves them with PUT
#   - the server lowering a bed target is reported
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

from hydra_suite import access
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import HydraConnection

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class Server:
    """What the fake server answers, and what it was asked."""

    requests: list = []
    answers: dict = {}  # "METHOD /path" -> (status, body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        path = self.path.split("?")[0]
        Server.requests.append((self.command, self.path, json.loads(raw) if raw else None))
        status, body = Server.answers.get(f"{self.command} {path}", (200, {"success": True}))
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PUT = do_DELETE = _answer


def start_http():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def reset(**answers):
    Server.requests = []
    Server.answers = answers


def make_conn(port, role="operator"):
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=port, username="ana", password="pw"))
    conn._token = "tok"
    conn.role = role
    conn.state = HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [{"id": 1, "name": "A", "model": "Parol6 (6-DOF)"}, {"id": 2, "name": "B", "model": "Z1 (6-DOF)"}]}]})
    return conn


def commands():
    return [(path, body) for method, path, body in Server.requests if path.endswith("/command")]


async def run(port):
    access.reset_controller_id("suite-test")
    access.MODES.modes.clear()
    access.MODES.default_mode = "live"

    # --- the controller id travels with the command, the claim, the release and the arming ---
    conn = make_conn(port)
    reset()
    await conn.send_command(2, "speed", {"speed": 50})
    check("command: carries the controller id", commands()[0][1].get("controllerId"), "suite-test")
    await conn.claim_robot(1, ttl_ms=60000, reason="bench")
    await conn.release_robot(1)
    armed = await conn.arm_jog(1, True, ttl_ms=30000)
    posts = {path: body for method, path, body in Server.requests if method == "POST"}
    check("claim: carries the controller id and what was asked", (posts["/api/robot/1/claim"]["controllerId"], posts["/api/robot/1/claim"]["ttlMs"], posts["/api/robot/1/claim"]["reason"]), ("suite-test", 60000, "bench"))
    check("claim: a force claim is only sent when asked for", "force" in posts["/api/robot/1/claim"], False)
    check("release: carries the controller id", posts["/api/robot/1/release"]["controllerId"], "suite-test")
    check("jog-arm: carries the controller id and the arming", (posts["/api/robot/1/jog-arm"]["controllerId"], posts["/api/robot/1/jog-arm"]["armed"]), ("suite-test", True))
    await conn.claim_robot(1, force=True)
    check("claim: force when asked", [b for m, p, b in Server.requests if p.endswith("/claim")][-1]["force"], True)

    # --- the refusals read differently ---
    messages = []
    conn.error.connect(messages.append)
    for code, status, expected in (
        ("other-account", 409, "MSG_NET_REJ_OTHER_ACCOUNT"),
        ("other-controller", 409, "MSG_NET_REJ_OTHER_CONTROLLER"),
        ("controller-id-required", 409, "MSG_NET_REJ_CONTROLLER_REQUIRED"),
        ("jog-not-armed", 403, "MSG_NET_REJ_NOT_ARMED"),
        (None, 409, "MSG_NET_REJ_RESERVED"),
    ):
        reset(**{"POST /api/robot/2/command": (status, {"error": "refused here", **({"code": code} if code else {})})})
        messages.clear()
        await conn.send_command(2, "speed", {"speed": 50})
        check(f"refusal: {code or 'no code'} gets its own sentence", messages and messages[0] == _(expected, what=_("MSG_NET_WHAT_COMMAND"), detail="refused here"), True)
    sentences = {_(k, what="x", detail="y") for k in ("MSG_NET_REJ_OTHER_ACCOUNT", "MSG_NET_REJ_OTHER_CONTROLLER", "MSG_NET_REJ_CONTROLLER_REQUIRED", "MSG_NET_REJ_NOT_ARMED")}
    check("refusal: the four coded sentences differ", len(sentences), 4)

    for code, status, expected in (("other-account", 409, "claim_other_account"), ("other-controller", 409, "claim_other_controller"), ("controller-id-required", 400, "claim_controller_required")):
        reset(**{"POST /api/robot/1/claim": (status, {"error": "x", "code": code})})
        result = await conn.claim_robot(1)
        check(f"claim refused: {code}", (result.ok, result.code, result.status), (False, expected, status))
    reset(**{"POST /api/robot/1/jog-arm": (409, {"error": "held", "code": "other-account"})})
    check("arming refused by a reservation", (await conn.arm_jog(1, True)).code, "claim_other_account")
    reset(**{"POST /api/robot/1/jog-arm": (200, {"success": True, "armed": True, "expiresAt": time.time() * 1000 + 30000})})
    await conn.arm_jog(1, True)
    check("arming: remembered until it ends", access.is_armed(conn.jog_armed_until.get(1)), True)
    reset()
    await conn.arm_jog(1, False)
    check("disarming forgets it", conn.jog_armed_until.get(1), None)

    # --- Sim: nothing that moves leaves the program ---
    access.MODES.set_mode("127.0.0.1:%d" % port, 1, "sim")
    messages.clear()
    reset()
    for command in ("jog", "play", "reset", "tool", "valve", "pump", "trajectory", "speed"):
        await conn.send_command(1, command, {"axis": "x", "amount": 1})
    check("sim: eight real commands, no request", commands(), [])
    check("sim: each one is said to the operator", len(messages), 8)
    check("sim: with the Sim sentence", messages[0], _("MSG_NET_SIM_BLOCKED", command="jog", robot=1))
    await conn.send_command(1, "stop", {})
    await conn.send_command(1, "pause", {})
    check("sim: STOP and pause still go out", [b["command"] for p, b in commands()], ["stop", "pause"])
    await conn.send_command(2, "jog", {"axis": "x", "amount": 1})
    check("sim: another robot is not affected", commands()[-1][0], "/api/robot/2/command")
    access.MODES.modes.clear()

    # --- a jog above the limit of its model ---
    conn.safety = access.parse_safety_limits({"limits": {"jog": {"default": {"maxAmount": 100, "maxAbsolute": 1000}, "models": {"parol6": {"maxAmount": 20}}}}})
    reset()
    messages.clear()
    await conn.send_command(1, "jog", {"axis": "x", "amount": 25, "target": "robot"})
    check("jog: above the limit of the model, nothing is sent", commands(), [])
    check("jog: and the operator is told the limit", messages, [_("MSG_NET_JOG_LIMIT", limit="20")])
    await conn.send_command(1, "jog", {"axis": "x", "amount": 15, "target": "robot"})
    await conn.send_command(2, "jog", {"axis": "x", "amount": 90, "target": "robot"})
    check("jog: inside the limit it goes out", [p for p, b in commands()], ["/api/robot/1/command", "/api/robot/2/command"])
    await conn.send_command(1, "jog", {"axis": "x", "amount": 0, "target": "robot", "joints": {"j1": 1}})
    check("jog: a pure joint move (amount 0) goes out", len(commands()), 3)

    # --- reservations and limits read from the server ---
    now = time.time() * 1000
    reset(**{
        "GET /api/claims": (200, {"claims": [{"robotId": 1, "robotName": "A", "ownerUsername": "ana", "controllerId": "suite-test", "expiresAt": now + 90000}]}),
        "GET /api/safety-limits": (200, {"limits": {"jog": {"armRequired": True, "armTtlMs": 45000}, "claims": {"requireControllerId": True}}, "robot": {"id": 1, "jogArmedUntil": now + 20000}}),
    })
    check("refresh: read", await conn.refresh_access(1), True)
    check("refresh: asked for the limits of that robot", any(p == "/api/safety-limits?robotId=1" for m, p, b in Server.requests), True)
    check("refresh: the reservations", [(c.robot_id, c.controller_id) for c in conn.claims], [(1, "suite-test")])
    check("refresh: the limits", (conn.safety.limits.arm_required, conn.safety.limits.arm_ttl_ms, conn.safety.limits.require_controller_id), (True, 45000, True))
    check("refresh: until when the jog is armed", access.is_armed(conn.jog_armed_until.get(1)), True)
    reset(**{"GET /api/claims": (404, {"error": "no"}), "GET /api/safety-limits": (404, {"error": "no"})})
    check("refresh: a server without the routes keeps what it had", (await conn.refresh_access(1), conn.safety.limits.arm_required), (False, True))

    # --- an administrator saves the limits ---
    saved_answer = {"success": True, "limits": {"claims": {"requireControllerId": True}}}
    reset(**{"PUT /api/admin/safety-limits": (200, saved_answer)})
    result = await conn.put_safety_limits({"claims": {"requireControllerId": True}})
    put = [(m, p, b) for m, p, b in Server.requests if m == "PUT"][0]
    check("save: PUT with the patch as it is", (put[1], put[2]), ("/api/admin/safety-limits", {"claims": {"requireControllerId": True}}))
    check("save: the state is the one the server now holds", (result.ok, conn.safety.limits.require_controller_id), (True, True))
    reset(**{"PUT /api/admin/safety-limits": (400, {"error": "jog.armTtlMs out of range"})})
    refused = await conn.put_safety_limits({"jog": {"armTtlMs": 5}})
    check("save: a refusal says why and changes nothing", (refused.ok, refused.detail, conn.safety.limits.require_controller_id), (False, "jog.armTtlMs out of range", True))

    # --- a bed target lowered by the server ---
    conn.role = "admin"  # only an administrator saves the tree
    reset(**{"POST /api/settings": (200, {"success": True, "warnings": [{"robotId": 1, "field": "heatedBed.targetTemp", "requested": 300, "applied": 110, "code": "temperature-limit"}]})})
    conn._ws = None
    conn.state.raw["settings"] = {"x": 1}
    messages.clear()
    await conn.push_state()
    check("settings: a lowered bed target is reported", messages, [_("MSG_NET_TEMP_LOWERED", requested="300", applied="110")])

    # --- an operator's edit of the settings tree is not sent ---
    operator = make_conn(port)
    operator.role = "operator"
    operator._ws = None
    operator.state.raw["settings"] = {"y": 2}
    reset()
    told = []
    operator.error.connect(told.append)
    await operator.push_state()
    check("operator: the tree is not sent", [m for m, p, b in Server.requests if p == "/api/settings"], [])
    check("operator: and the person is told once that it stays in this window", told, [_("MSG_NET_OPERATOR_LOCAL_ONLY")])
    operator.state.raw["settings"] = {"y": 3}
    await operator.push_state()
    check("operator: a second edit does not repeat it", (len(told), len(Server.requests)), (1, 0))
    operator.role = "admin"
    operator.state.raw["settings"] = {"y": 4}
    reset()
    await operator.push_state()
    check("admin: the same edit is sent", [m for m, p, b in Server.requests if p == "/api/settings"], ["POST"])

    # --- the user accounts ---
    reset(**{"GET /api/users": (200, {"users": [{"username": "admin", "role": "admin", "createdAt": "x"}]})})
    listed = await conn.fetch_users()
    check("users: the accounts are read", (listed.ok, [u["username"] for u in listed.body["users"]]), (True, ["admin"]))
    reset()
    await conn.create_user("bob", "long-enough-1", "operator")
    sent = [(m, p, b) for m, p, b in Server.requests][0]
    check("users: a new account goes out with its role", (sent[0], sent[1], sent[2]["username"], sent[2]["role"]), ("POST", "/api/users", "bob", "operator"))
    reset()
    await conn.update_user("a b/c", new_username=" bobby ", password="", role="admin")
    sent = Server.requests[0]
    check("users: a change goes to the quoted name, only with what changes", (sent[0], sent[1], sent[2]), ("PUT", "/api/users/a%20b%2Fc", {"newUsername": "bobby", "role": "admin"}))
    reset(**{"DELETE /api/users/bob": (400, {"error": "Cannot delete the last remaining admin account"})})
    refused = await conn.delete_user("bob")
    check("users: a refused delete says why", (Server.requests[0][:2], refused.ok, refused.detail), (("DELETE", "/api/users/bob"), False, "Cannot delete the last remaining admin account"))

    # --- nothing answers ---
    dead = make_conn(1)
    check("claim: no server is a network failure", (await dead.claim_robot(1)).code, "network")
    check("refresh: no server", await dead.refresh_access(1), False)


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    port = start_http().server_address[1]
    loop.run_until_complete(run(port))
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
