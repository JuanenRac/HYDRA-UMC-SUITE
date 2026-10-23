# =============================================================================
# HYDRA-UMC SUITE - tests/verify_stop_all.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies the global STOP, against a small real HTTP server on localhost (no
# robot, no real HYDRA-UMC-SERVER):
#   - net/client.py: POST /api/stop-all with the bearer token and no body, the
#     per-robot result (stopped / failed / reserved by another account /
#     persisted), one retry on a network error, "not confirmed" when nothing
#     answers or the server refuses, and the per-robot stop of every known
#     robot when the server rate limits (429)
#   - app.py: one STOP reaches every server of the swarm, a server that does
#     not confirm leaves the whole STOP "not confirmed" until a later one
#     confirms everywhere, no server at all is "not confirmed" too
#   - the texts (describe_stop_all) are warnings, not green, for every case
#     that is not clean
#   - the Qt Quick interface: the header button and the F12 shortcut call the
#     bridge's stopAll(), with no confirmation, and its result shows as text
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

import qasync
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication

from hydra_suite.app import StopAllSummary, SuiteController, describe_stop_all
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net import client as client_module
from hydra_suite.net.client import HydraConnection, StopAllResult

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


CLEAN_ANSWER = {
    "success": True,
    "stoppedCount": 2,
    "failedCount": 0,
    "persisted": True,
    "robots": [
        {"robotId": 1, "controllerId": "c1", "name": "A", "stopped": True, "valvesOff": True, "pumpsOff": True},
        {"robotId": 2, "controllerId": "c1", "name": "B", "stopped": True, "valvesOff": True, "pumpsOff": True, "reservedBy": "alice"},
    ],
}
PARTIAL_ANSWER = {
    "success": False,
    "stoppedCount": 1,
    "failedCount": 1,
    "persisted": False,
    "robots": [
        {"robotId": 1, "controllerId": "c1", "name": "A", "stopped": True, "valvesOff": True, "pumpsOff": True},
        {"robotId": 2, "controllerId": "c1", "name": "B", "stopped": False, "valvesOff": False, "pumpsOff": False, "error": "no link"},
    ],
}


class Behaviour:
    stop_all_status = 200
    stop_all_body = CLEAN_ANSWER
    drop_first = 0  # connections cut before answering, then normal
    requests: list = []
    command_requests: list = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if self.path == "/api/stop-all":
            Behaviour.requests.append((self.command, self.path, self.headers.get("Authorization"), self.headers.get("X-Hydra-Client"), raw))
            if Behaviour.drop_first > 0:
                Behaviour.drop_first -= 1
                self.connection.close()
                return
            payload = json.dumps(Behaviour.stop_all_body).encode()
            self.send_response(Behaviour.stop_all_status)
        elif self.path.endswith("/command"):
            Behaviour.command_requests.append((self.path, json.loads(raw or b"{}")))
            payload = b"{}"
            self.send_response(200)
        else:
            payload = b"{}"
            self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def start_http():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def reset(status=200, body=CLEAN_ANSWER, drop_first=0):
    Behaviour.stop_all_status = status
    Behaviour.stop_all_body = body
    Behaviour.drop_first = drop_first
    Behaviour.requests = []
    Behaviour.command_requests = []


def make_conn(port):
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=port))
    conn._token = "tok"
    conn.state = HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [
                {
                    "id": "c1",
                    "robots": [
                        {"id": 1, "name": "A", "playbackState": {"isPlaying": True}},
                        {"id": 2, "name": "B", "playbackState": {"isPlaying": True}},
                    ],
                }
            ],
        }
    )
    return conn


def playing(conn):
    return [r.is_playing for r in conn.state.controllers[0].robots]


async def run_client(port):
    client_module.STOP_ALL_RETRY_DELAY_S = 0.05

    reset()
    conn = make_conn(port)
    result = await conn.stop_all()
    method, path, auth, client_header, body = Behaviour.requests[0]
    check("client: POST", method, "POST")
    check("client: path", path, "/api/stop-all")
    check("client: bearer token", auth, "Bearer tok")
    check("client: client identity header", client_header, "suite")
    check("client: no body", body, b"")
    check("client: one request", len(Behaviour.requests), 1)
    check("client: clean result", result.is_clean, True)
    check("client: stopped count", result.stopped_count, 2)
    check("client: reservedBy of another account is kept", result.robots[1].reserved_by, "alice")
    check("client: the local mirror shows both robots stopped", playing(conn), [False, False])

    reset(body=PARTIAL_ANSWER)
    conn = make_conn(port)
    result = await conn.stop_all()
    check("partial: not clean", result.is_clean, False)
    check("partial: persisted false", result.persisted, False)
    check("partial: the failed robot", [r.robot_id for r in result.failed_robots], [2])
    check("partial: its error", result.failed_robots[0].error, "no link")
    check("partial: only the stopped robot is stopped locally", playing(conn), [False, True])

    reset(drop_first=1)
    conn = make_conn(port)
    result = await conn.stop_all()
    check("retry: a dropped connection is retried once", len(Behaviour.requests), 2)
    check("retry: and the retry confirms", result.confirmed, True)

    reset(drop_first=5)
    conn = make_conn(port)
    result = await conn.stop_all()
    check("no answer: exactly two attempts", len(Behaviour.requests), 2)
    check("no answer: not confirmed", result.confirmed, False)
    check("no answer: nothing is shown as stopped", playing(conn), [True, True])

    reset(status=500, body={"error": "boom"})
    conn = make_conn(port)
    result = await conn.stop_all()
    check("500: not confirmed and not retried", (result.confirmed, len(Behaviour.requests)), (False, 1))

    reset(status=403, body={"error": "Access denied"})
    conn = make_conn(port)
    result = await conn.stop_all()
    check("403: not confirmed", result.confirmed, False)

    reset(status=429, body={"error": "too many requests"})
    conn = make_conn(port)
    result = await conn.stop_all()
    sent = sorted(p for p, _b in Behaviour.command_requests)
    check("429: falls back to the stop of every known robot", sent, ["/api/robot/1/command", "/api/robot/2/command"])
    check("429: with the stop command", {b["command"] for _p, b in Behaviour.command_requests}, {"stop"})
    check("429: flagged as sent one by one", result.via_fallback, True)
    check("429: both stopped", result.stopped_count, 2)
    check("429: the local mirror shows both robots stopped", playing(conn), [False, False])

    check("parse: counts are derived when the server omits them", StopAllResult.from_json({"robots": [{"robotId": 3, "stopped": False}]}).failed_count, 1)


async def run_controller(port):
    reset()
    controller = SuiteController()
    summaries = []
    controller.stop_all_changed.connect(summaries.append)

    controller._stop_all_sync = None
    await controller._stop_all()
    check("controller: no server is not confirmed", summaries[-1].state, "not_confirmed")
    check("controller: no server has a reason", bool(summaries[-1].reason), True)

    good = make_conn(port)
    bad_port = start_http().server_address[1]
    other = make_conn(bad_port)
    controller.connections = {"good": good, "other": other}
    summaries.clear()
    await controller._stop_all()
    check("controller: sending first, then the result", [s.state for s in summaries], ["sending", "done"])
    check("controller: both servers were called", len(Behaviour.requests), 2)
    check("controller: the totals add up", summaries[-1].stopped, 4)

    Behaviour.drop_first = 100
    summaries.clear()
    await controller._stop_all()
    check("controller: a server that does not answer leaves the STOP not confirmed", summaries[-1].state, "not_confirmed")
    headline, details, severity = describe_stop_all(summaries[-1])
    check("controller: that is shown as an error", severity, "error")
    check("controller: with the standard text", headline, _("STOP_ALL_NOT_CONFIRMED"))
    check("controller: and names the server", any("good" in d or "other" in d for d in details), True)

    reset()
    summaries.clear()
    await controller._stop_all()
    check("controller: a later STOP that confirms everywhere clears it", summaries[-1].state, "done")
    check("controller: the stored summary is the latest", controller.stop_all_summary.state, "done")


def check_texts():
    clean = StopAllSummary("done", {"s": StopAllResult.from_json(CLEAN_ANSWER)})
    headline, details, severity = describe_stop_all(clean)
    check("text: clean is ok", severity, "ok")
    check("text: clean names the count", "2" in headline, True)
    check("text: a reservation by another account is listed", any("alice" in d for d in details), True)

    partial = StopAllSummary("done", {"s": StopAllResult.from_json(PARTIAL_ANSWER)})
    headline, details, severity = describe_stop_all(partial)
    check("text: a failed robot is an error, not green", severity, "error")
    check("text: the failed robot and its reason are listed", any("B" in d and "no link" in d for d in details), True)
    check("text: an unsaved stop is warned about", any(_("STOP_ALL_NOT_SAVED", server="s") == d for d in details), True)
    check("text: sending is busy", describe_stop_all(StopAllSummary("sending"))[2], "busy")


def check_qml_shell():
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    import qt_suite

    QQuickStyle.setStyle("Basic")
    controller = SuiteController()
    calls = []
    controller.stop_all = lambda: calls.append("stop")
    bridge = qt_suite.SuiteQtBridge(
        controller,
        frame_provider=qt_suite.CameraFrameProvider(),
        viewport_frame_provider=qt_suite.ViewportFrameProvider(),
        media_frame_provider=qt_suite.MediaFrameProvider(),
    )
    engine = QQmlApplicationEngine()
    engine.addImageProvider("cameraFrames", bridge._frame_provider)
    engine.addImageProvider("viewportFrame", bridge._viewport_frame_provider)
    engine.addImageProvider("vacuumFrame", bridge._vacuum_frame_provider)
    engine.addImageProvider("cameraMedia", bridge._media_frame_provider)
    engine.addImageProvider("catalogFrame", qt_suite.ViewportFrameProvider())
    engine.rootContext().setContextProperty("suiteBackend", bridge)
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(qt_suite.QML_PATH)))
    roots = engine.rootObjects()
    check("qml: the shell loads", len(roots) > 0, True)
    if not roots:
        return
    button = roots[0].findChild(QObject, "stopAllButton")
    check("qml: the header has the STOP button", button is not None, True)
    bridge.stopAll()
    check("qml: the bridge's stopAll() reaches the controller", calls, ["stop"])
    controller.stop_all_changed.emit(StopAllSummary("not_confirmed", reason="x"))
    check("qml: a not-confirmed STOP is an error text", (bridge.stopAllSeverity, bridge.stopAllText), ("error", _("STOP_ALL_NOT_CONFIRMED")))
    controller.stop_all_changed.emit(StopAllSummary("done", {"s": StopAllResult.from_json(CLEAN_ANSWER)}))
    check("qml: a clean result is ok", bridge.stopAllSeverity, "ok")
    source = qt_suite.QML_PATH.read_text(encoding="utf-8")
    check("qml: F12 is an application-wide shortcut", 'sequence: "F12"' in source and "Qt.ApplicationShortcut" in source, True)


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    port = start_http().server_address[1]

    loop.run_until_complete(run_client(port))
    loop.run_until_complete(run_controller(port))
    check_texts()
    check_qml_shell()

    if failures:
        print(f"{failures} check(s) failed")
        sys.exit(1)
    print("verify_stop_all: PASS")


main()
