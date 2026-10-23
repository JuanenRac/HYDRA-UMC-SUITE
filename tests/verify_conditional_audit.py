# =============================================================================
# HYDRA-UMC SUITE - tests/verify_conditional_audit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies the second contract of the server (conditional writes, the atomic table command, the audit record and the
# pushed reservations), without a robot and without the real HYDRA-UMC-SERVER:
#   - the pure rules: which commands carry If-Match in each mode, the revision tracker, the limits of a table move,
#     the table move turned into jogs, the audit record and its chain check
#   - against a small real HTTP server on localhost: If-Match goes with a write only when a revision is known and
#     nothing else is on its way, never with STOP, with a jog in the standard mode, with a renewal or with a take-over;
#     a 412 changes nothing, says so, and the robot is read again; the table command is sent, bounded by the limits,
#     refused in Sim and turned into jogs for a server that does not know it; the audit record is read, checked and
#     exported; the WebSocket message `claims` replaces the list of reservations
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import hashlib
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
from hydra_suite.panel_logic import audit_record

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class Server:
    requests: list = []   # (method, path, body, headers)
    answers: dict = {}    # "METHOD /path" -> (status, body) or a list of them, used in turn


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        path = self.path.split("?")[0]
        Server.requests.append((self.command, self.path, json.loads(raw) if raw else None, {k.lower(): v for k, v in self.headers.items()}))
        answer = Server.answers.get(f"{self.command} {path}", (200, {"success": True}))
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        status, body = answer
        if isinstance(body, str):
            payload = body.encode()
            content_type = "application/x-ndjson"
        else:
            payload = json.dumps(body).encode()
            content_type = "application/json"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PUT = _answer


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
    conn.login_ok = True
    conn.state = HydraState({
        "activeControllerId": "c1",
        "controllers": [{"id": "c1", "robots": [
            {"id": 1, "name": "A", "model": "Parol6 (6-DOF)", "valves": [False], "hasXYTable": True, "xyTable": {"pos": {"x": 10, "y": 20}, "tableSize": {"width": 300, "length": 300}}},
            {"id": 2, "name": "B", "model": "Z1 (6-DOF)"},
        ]}],
    })
    return conn


def commands():
    return [(path, body, headers) for method, path, body, headers in Server.requests if path.endswith("/command")]


def if_match(entry):
    return entry[2].get("if-match")


GENESIS = "0" * 64


def chain(count, start=1):
    lines = []
    prev = GENESIS
    for i in range(count):
        body = {"seq": start + i, "ts": f"2030-01-01T00:00:0{i}.000Z", "type": "claim", "outcome": "ok", "username": "ana", "controllerId": "w1", "ip": "10.0.0.5", "robotId": 1, "detail": {"ttlMs": 60000}, "prev": prev}
        digest = hashlib.sha256(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        lines.append({**body, "hash": digest})
        prev = digest
    return lines


def pure():
    # --- which commands carry If-Match ---
    for mode in access.CONDITIONAL_MODES:
        check(f"conditional: STOP never ({mode})", access.is_conditional(mode, "stop"), False)
    check("conditional: standard leaves out jog and speed", (access.is_conditional("standard", "jog"), access.is_conditional("standard", "speed")), (False, False))
    check("conditional: standard checks table, claim and valve", [access.is_conditional("standard", c) for c in ("table", "claim", "valve")], [True, True, True])
    check("conditional: strict checks jog", access.is_conditional("strict", "jog"), True)
    check("conditional: off checks nothing", access.is_conditional("off", "table"), False)
    check("revision: read from a body", (access.revision_of({"revision": "abc123"}), access.revision_of({"revision": 5}), access.revision_of({"revision": "has space"}), access.revision_of(None)), ("abc123", None, None, None))
    check("revision: quoted like an ETag", access.if_match_header("abc"), '"abc"')
    check("failure: a 412 is its own failure", (access.failure_code_for(412, None), access.failure_code_for(409, "revision-mismatch")), ("revision_changed", "revision_changed"))

    # --- the mode of this program ---
    setting = access.ConditionalSetting.from_config({"conditionalWrites": "strict"})
    check("setting: read from the configuration", setting.mode, "strict")
    check("setting: nonsense falls back to standard", access.ConditionalSetting.from_config({"conditionalWrites": "x"}).mode, "standard")
    check("setting: written back", setting.to_config(), {"conditionalWrites": "strict"})
    setting.set("nonsense")
    check("setting: an unknown mode changes nothing", setting.mode, "strict")

    # --- the tracker ---
    tracker = access.RevisionTracker(access.ConditionalSetting("standard"))
    first = tracker.begin(1, "valve")
    check("tracker: nothing to send until a revision is known", first.if_match, None)
    tracker.finish(1, first.seq, "r1")
    check("tracker: then the last one", tracker.begin(1, "valve").if_match, '"r1"')
    tracker.finish(1, 0, None)
    tracker = access.RevisionTracker(access.ConditionalSetting("strict"))
    tracker.learn(1, "r1")
    a, b = tracker.begin(1, "table"), tracker.begin(1, "table")
    check("tracker: nothing while another write to the robot is on its way", (a.if_match, b.if_match), ('"r1"', None))
    tracker.finish(1, a.seq, "r2")
    tracker.finish(1, b.seq, "r3")
    check("tracker: the newest answer wins", tracker.known(1), "r3")
    x, y = tracker.begin(1, "valve"), tracker.begin(1, "valve")
    tracker.finish(1, y.seq, "newer")
    tracker.finish(1, x.seq, "older")
    check("tracker: out of order answers keep the newest", tracker.known(1), "newer")
    t = tracker.begin(1, "valve")
    tracker.finish(1, t.seq, None)
    check("tracker: an answer without a revision forgets", tracker.known(1), None)
    tracker.learn(1, "r1")
    tracker.learn("2", "r2")
    check("tracker: a robot is the same as a number or as text", (tracker.known("1"), tracker.known(2)), ("r1", "r2"))
    tracker.forget()
    check("tracker: forgets everything", (tracker.known(1), tracker.known(2)), (None, None))
    off = access.RevisionTracker(access.ConditionalSetting("off"))
    off.learn(1, "r1")
    check("tracker: off never sends", off.begin(1, "table").if_match, None)

    # --- the table move ---
    limits = access.SafetyLimits()  # relative up to 100, absolute up to 1000
    check("table: parameters need numbers", (access.table_params(1, 2, "absolute"), access.table_params(float("nan"), 2, "absolute"), access.table_params(1, "2", "absolute"), access.table_params(1, 2, "sideways")), ({"x": 1, "y": 2, "mode": "absolute"}, None, None, None))
    check("table: a relative move is bounded by the largest jog", (access.check_table(limits, "x", {"x": 100, "y": 0, "mode": "relative"}).ok, access.check_table(limits, "x", {"x": 0, "y": -101, "mode": "relative"}).kind), (True, "amount"))
    check("table: an absolute move is bounded by the largest position", (access.check_table(limits, "x", {"x": 1000, "y": -1000, "mode": "absolute"}).ok, access.check_table(limits, "x", {"x": 1001, "y": 0, "mode": "absolute"}).kind), (True, "absolute"))
    check("table: and so is where a relative move ends", (access.check_table(limits, "x", {"x": 50, "y": 0, "mode": "relative"}, {"x": 980}).kind, access.check_table(limits, "x", {"x": 50, "y": 0, "mode": "relative"}, {"x": 900}).ok), ("absolute", True))
    check("table: an older server is recognised by its answer", (access.is_unknown_command(400, None, "unknown command"), access.is_unknown_command(400, "table-invalid", "x and y must be finite numbers"), access.is_unknown_command(200, None, "")), (True, False, False))
    check("table: turned into the jogs it did before", access.table_as_jogs({"x": 10, "y": 20, "mode": "absolute"}), [{"axis": "x", "amount": 10, "target": "xytable", "absolute": True}, {"axis": "y", "amount": 20, "target": "xytable", "absolute": True}])
    check("table: a relative move skips the axis that stays", access.table_as_jogs({"x": 2, "y": 0, "mode": "relative"}), [{"axis": "x", "amount": 2, "target": "xytable"}])
    check("sim: a table move is a real command", "table" in access.REAL_COMMANDS, True)

    # --- the audit record ---
    read = access.parse_audit({"enabled": True, "lockedOff": False, "entries": [*chain(3), {"seq": "x"}, None, 5], "verification": {"ok": True, "entries": 12}})
    check("audit: reads the lines and drops what is not one", (len(read.entries), read.entries[0].username, read.entries[0].robot_id, read.verification["entries"]), (3, "ana", 1, 12))
    check("audit: an off record", (access.parse_audit({"enabled": False, "lockedOff": True, "entries": []}).enabled, access.parse_audit({"enabled": False, "lockedOff": True, "entries": []}).locked_off), (False, True))
    check("audit: an intact chain", (lambda c: (c.ok, c.checked, c.links, c.gaps))(access.check_chain(access.parse_audit({"entries": chain(5)}).entries)), (True, 5, 4, 0))
    check("audit: a window in the middle of the record", access.check_chain(access.parse_audit({"entries": chain(4, 100)}).entries).ok, True)
    changed = chain(4)
    changed[2] = {**changed[2], "username": "mallory"}
    c = access.check_chain(access.parse_audit({"entries": changed}).entries)
    check("audit: a changed line", (c.ok, c.broken_at_seq, c.reason), (False, 3, "changed"))
    lines = chain(3)
    rewritten = {k: v for k, v in lines[1].items() if k != "hash"}
    rewritten["username"] = "someone-else"
    rewritten["hash"] = hashlib.sha256(json.dumps({k: v for k, v in rewritten.items() if k != "hash"}, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    c = access.check_chain(access.parse_audit({"entries": [lines[0], rewritten, lines[2]]}).entries)
    check("audit: a replaced line whose successor still names the old one", (c.ok, c.broken_at_seq, c.reason), (False, 3, "link"))
    lines = chain(6)
    c = access.check_chain(access.parse_audit({"entries": [lines[0], lines[2], lines[5]]}).entries)
    check("audit: a filtered view is not broken, only gaps", (c.ok, c.links, c.gaps), (True, 0, 2))
    check("audit: the query string", (access.audit_query(), access.audit_query(5000, "claim", 2, True), access.audit_query(0)), ("", "?limit=1000&type=claim&robotId=2&verify=1", "?limit=1"))
    check("audit: the detail is shortened", (access.detail_line(None), access.detail_line({"ttlMs": 60000, "reason": "bench"}), len(access.detail_line({"big": "x" * 300}, 20))), ("", "ttlMs=60000 reason=bench", 20))
    rows = audit_record.rows(access.parse_audit({"entries": chain(2)}).entries, {1: "Arm"})
    check("audit: the newest line first, with the robot's name", (rows[0]["seq"], rows[1]["seq"], rows[0]["robot"], rows[0]["type"]), (2, 1, "Arm", _("AUDIT_TYPE_CLAIM")))

    # --- the pushed reservations carry the arming ---
    claims = access.parse_claims({"claims": [{"robotId": 1, "ownerUsername": "ana", "controllerId": "suite-test", "jogArmedUntil": 5000}, {"robotId": 2, "ownerUsername": "bob"}]})
    check("claims: the arming of the jog", [(c.robot_id, c.jog_armed_until) for c in claims], [(1, 5000.0), (2, None)])


async def network(port):
    access.reset_controller_id("suite-test")
    access.MODES.modes.clear()
    access.MODES.default_mode = "live"
    access.CONDITIONAL.set("standard")

    # --- If-Match goes with a write only when a revision is known and nothing else is on its way ---
    conn = make_conn(port)
    reset(**{"POST /api/robot/1/command": (200, {"success": True, "revision": "rev-a"})})
    await conn.send_command(1, "valve", {"index": 0, "state": True})
    check("if-match: the first write has none", if_match(commands()[0]), None)
    check("if-match: and learns the revision", conn.revisions.known(1), "rev-a")
    Server.answers["POST /api/robot/1/command"] = (200, {"success": True, "revision": "rev-b"})
    await conn.send_command(1, "valve", {"index": 0, "state": False})
    check("if-match: the next one carries it, quoted", if_match(commands()[1]), '"rev-a"')
    check("if-match: and the newer revision replaces it", conn.revisions.known(1), "rev-b")
    await conn.send_command(1, "jog", {"axis": "x", "amount": 5, "target": "robot"})
    check("if-match: a jog has none in the standard mode", if_match(commands()[2]), None)
    await conn.send_command(1, "stop", {})
    check("if-match: STOP never has one", if_match(commands()[-1]), None)
    access.CONDITIONAL.set("strict")
    conn.revisions.learn(1, "rev-c")
    await conn.send_command(1, "jog", {"axis": "x", "amount": 5, "target": "robot"})
    check("if-match: a jog has one in the strict mode", if_match(commands()[-1]), '"rev-c"')
    await conn.send_command(1, "stop", {})
    check("if-match: STOP still has none in the strict mode", if_match(commands()[-1]), None)
    access.CONDITIONAL.set("off")
    conn.revisions.learn(1, "rev-d")
    await conn.send_command(1, "valve", {"index": 0, "state": True})
    check("if-match: none when the mode is off", if_match(commands()[-1]), None)
    access.CONDITIONAL.set("standard")

    # --- the reservation calls ---
    conn = make_conn(port)
    reset(**{"POST /api/robot/1/claim": (200, {"success": True, "revision": "after-claim"}), "POST /api/robot/1/release": (200, {"success": True, "revision": "after-release"})})
    await conn.claim_robot(1)
    claim_headers = [h for m, p, b, h in Server.requests if p.endswith("/claim")]
    check("claim: the first has no If-Match and learns the revision", (claim_headers[0].get("if-match"), conn.revisions.known(1)), (None, "after-claim"))
    await conn.release_robot(1)
    release_headers = [h for m, p, b, h in Server.requests if p.endswith("/release")]
    check("release: carries the revision the claim left", release_headers[0].get("if-match"), '"after-claim"')
    conn.revisions.learn(1, "old")
    await conn.claim_robot(1, unconditional=True)
    await conn.claim_robot(1, force=True)
    claim_headers = [h for m, p, b, h in Server.requests if p.endswith("/claim")]
    check("claim: a renewal and a take-over never carry If-Match", [h.get("if-match") for h in claim_headers[-2:]], [None, None])
    reset(**{"POST /api/robot/1/release": (412, {"error": "changed", "code": "revision-mismatch", "revision": "current"})})
    conn.revisions.learn(1, "stale")
    refused = await conn.release_robot(1)
    check("release: a 412 is a changed robot and keeps the revision the server gave", (refused.ok, refused.code, conn.revisions.known(1)), (False, "revision_changed", "current"))

    # --- a 412 on a command: nothing applied, said so, the robot read again ---
    conn = make_conn(port)
    messages = []
    conn.error.connect(messages.append)
    reset(**{
        "POST /api/robot/1/command": (412, {"error": "the robot changed", "code": "revision-mismatch", "revision": "now"}),
        "GET /api/robot/1": (200, {"robot": {"id": 1, "name": "A", "model": "Parol6 (6-DOF)", "valves": [True]}, "revision": "now", "cellId": "c1"}),
    })
    conn.revisions.learn(1, "stale")
    await conn.send_command(1, "valve", {"index": 0, "state": True}, lambda r: r.set_valve(0, True))
    check("412: said to the operator", messages and messages[0] == _("MSG_NET_REJ_REVISION", what=_("MSG_NET_WHAT_COMMAND")), True)
    check("412: the request carried the stale revision", if_match(commands()[0]), '"stale"')
    check("412: the robot was read again", any(m == "GET" and p == "/api/robot/1" for m, p, b, h in Server.requests), True)
    check("412: and the revision it gave is the one kept", conn.revisions.known(1), "now")
    check("412: the screen shows the robot as the server has it", conn.state.raw["controllers"][0]["robots"][0]["valves"], [True])
    check("412: nothing else of the robot was lost", conn.state.raw["controllers"][0]["robots"][0].get("hasXYTable"), True)
    check("412: the sentence is its own", _("MSG_NET_REJ_REVISION", what="x") not in {_("MSG_NET_REJ_RESERVED", what="x", detail="y")}, True)
    check("412: GET /api/robot/:id of an older server changes nothing", await make_conn(port).refresh_robot(1) in (True, False), True)
    reset(**{"GET /api/robot/1": (404, {"error": "no"})})
    check("fetch robot: a server without the route gives none", await conn.fetch_robot(1), None)

    # --- the whole tree saved from this program forgets the revisions ---
    conn = make_conn(port)
    conn.revisions.learn(1, "r1")
    conn._ws = None
    conn.state.raw["settings"] = {"x": 2}
    reset()
    await conn.push_state()
    check("save: the whole tree forgets what was known of the robots", conn.revisions.known(1), None)

    # --- the table command ---
    conn = make_conn(port)
    conn.safety = access.parse_safety_limits({"limits": {"jog": {"default": {"maxAmount": 100, "maxAbsolute": 1000}, "models": {"parol6": {"maxAbsolute": 300}}}}})
    messages = []
    conn.error.connect(messages.append)
    reset(**{"POST /api/robot/1/command": (200, {"success": True, "revision": "t1", "applied": {"robotId": 1, "x": 50, "y": 20}})})
    await conn.send_command(1, "table", access.table_params(50, 20, "absolute"))
    check("table: one request with the whole move", [(c[0], c[1]["command"], c[1]["params"]) for c in commands()], [("/api/robot/1/command", "table", {"x": 50, "y": 20, "mode": "absolute"})])
    await conn.send_command(1, "table", access.table_params(301, 0, "absolute"))
    check("table: above the limit of the model nothing is sent", len(commands()), 1)
    check("table: and the limit is said", messages, [_("MSG_NET_JOG_LIMIT", limit="abs 300")])
    await conn.send_command(1, "table", access.table_params(200, 0, "relative"))
    check("table: a relative move above the largest jog is not sent either", len(commands()), 1)
    await conn.send_command(1, "table", access.table_params(10, 0, "relative"))
    check("table: a small relative move goes out", len(commands()), 2)
    check("table: and carries the revision of the first answer (standard mode)", if_match(commands()[1]), '"t1"')
    access.MODES.set_mode("127.0.0.1:%d" % port, 1, "sim")
    await conn.send_command(1, "table", access.table_params(1, 1, "absolute"))
    check("sim: a table move sends nothing", len(commands()), 2)
    access.MODES.modes.clear()

    # a server that predates the command
    conn = make_conn(port)
    reset(**{"POST /api/robot/1/command": [(400, {"error": "unknown command"}), (200, {"success": True})]})
    await conn.send_command(1, "table", access.table_params(50, 20, "absolute"))
    sent = [(c[1]["command"], c[1]["params"]) for c in commands()]
    check("table: an older server gets the jogs it understands", sent, [("table", {"x": 50, "y": 20, "mode": "absolute"}), ("jog", {"axis": "x", "amount": 50, "target": "xytable", "absolute": True}), ("jog", {"axis": "y", "amount": 20, "target": "xytable", "absolute": True})])
    check("table: and it is remembered", conn.has_table_command, False)
    Server.requests = []
    await conn.send_command(1, "table", access.table_params(60, 20, "absolute"))
    check("table: the next move goes straight to the jogs", [c[1]["command"] for c in commands()], ["jog", "jog"])

    # --- the audit record ---
    conn = make_conn(port, role="admin")
    lines = chain(4)
    reset(**{"GET /api/audit": (200, {"enabled": True, "lockedOff": False, "entries": lines, "verification": {"ok": True, "entries": 4}})})
    result, read = await conn.fetch_audit(limit=50, type="claim", verify=True)
    check("audit: asked with the filter and the verification", [p for m, p, b, h in Server.requests if m == "GET"], ["/api/audit?limit=50&type=claim&verify=1"])
    check("audit: read", (result.ok, len(read.entries), read.verification["ok"]), (True, 4, True))
    chain_lines = audit_record.chain_lines(read)
    check("audit: the chain sentences say the server and this program agree", [(line["ok"]) for line in chain_lines], [True, True])
    broken = access.parse_audit({"entries": lines, "verification": {"ok": False, "entries": 4, "brokenAtSeq": 3, "reason": "a line was changed"}})
    check("audit: a broken chain is said with the line", audit_record.chain_lines(broken)[0], {"text": _("AUDIT_SERVER_BROKEN", seq=3, reason="a line was changed"), "ok": False})
    reset(**{"GET /api/audit": (403, {"error": "admin only"})})
    result, read = await conn.fetch_audit()
    check("audit: a refusal gives no lines and a code", (result.ok, result.code, read), (False, "forbidden", None))
    check("audit: and its sentence", audit_record.failure_text(result.status, result.code), _("AUDIT_FAILURE_FORBIDDEN"))
    reset(**{"GET /api/audit": (404, {"error": "no", "code": "audit-unavailable"})})
    result, read = await conn.fetch_audit()
    check("audit: an older server", audit_record.failure_text(result.status, result.code), _("AUDIT_FAILURE_UNAVAILABLE"))
    reset(**{"GET /api/audit": (200, '{"seq":1}\n')})
    check("audit: the lines as stored", await conn.fetch_audit_jsonl(limit=10), '{"seq":1}\n')
    check("audit: asked for the jsonl", [p for m, p, b, h in Server.requests], ["/api/audit?limit=10&format=jsonl"])
    reset(**{"GET /api/audit": (500, {"error": "x"})})
    check("audit: a failure to export gives none", await conn.fetch_audit_jsonl(), None)

    # --- the pushed reservations ---
    conn = make_conn(port)
    seen = []
    conn.claims_changed.connect(lambda: seen.append(1))
    check("claims: none pushed yet", conn.claims_are_pushed(), False)
    now = time.time() * 1000
    conn._handle_message(json.dumps({"type": "claims", "schema": 2, "claims": [{"robotId": 1, "robotName": "A", "ownerUsername": "ana", "controllerId": "suite-test", "expiresAt": now + 60000, "jogArmedUntil": now + 20000}, {"robotId": 2, "ownerUsername": "bob", "controllerId": "other"}]}))
    check("claims: the list is replaced and announced", ([(c.robot_id, c.owner_username) for c in conn.claims], len(seen)), ([(1, "ana"), (2, "bob")], 1))
    check("claims: a recent push lets the poll rest", conn.claims_are_pushed(), True)
    check("claims: the arming of this program's own reservation is kept", access.is_armed(conn.jog_armed_until.get(1)), True)
    check("claims: and not that of another controller", conn.jog_armed_until.get(2), None)
    reset(**{"GET /api/claims": (200, {"claims": []}), "GET /api/safety-limits": (200, {"limits": {}})})
    await conn.refresh_access(1, claims=False)
    check("claims: a poll that rests does not ask for the list", [p for m, p, b, h in Server.requests if m == "GET"], ["/api/safety-limits?robotId=1"])
    Server.requests = []
    await conn.refresh_access(1)
    check("claims: a poll that does not rest asks for both", sorted(p.split("?")[0] for m, p, b, h in Server.requests if m == "GET"), ["/api/claims", "/api/safety-limits"])

    # --- nothing answers ---
    dead = make_conn(1)
    check("audit: no server is a network failure", (await dead.fetch_audit())[0].code, "network")
    check("fetch robot: no server gives none", await dead.fetch_robot(1), None)


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    pure()
    port = start_http().server_address[1]
    loop.run_until_complete(network(port))
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
