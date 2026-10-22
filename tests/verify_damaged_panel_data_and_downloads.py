# =============================================================================
# HYDRA-UMC SUITE - tests/verify_damaged_panel_data_and_downloads.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies, without hardware:
#   - the Kinematic Brain panel and the ATC panel keep working when the
#     controller record is half empty (no revolver fields, shorter fan / pump /
#     valve lists, a grid that is not text)
#   - the telemetry notices (series mixed in one line, result cut at the
#     service limit)
#   - HydraConnection.save_camera_media_to(): a saved recording is streamed to
#     disk in chunks with the bearer token, an error answer writes nothing and
#     leaves no partial file, an unwritable folder is a clean False
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, ".")

import qasync
from PySide6.QtWidgets import QApplication

from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import HydraConnection
from hydra_suite.ui.panels.atc_tools_panel import AtcToolsPanel
from hydra_suite.ui.panels.ecosystem_telemetry_panel import telemetry_notices
from hydra_suite.ui.panels.kinematic_brain_stage_panel import KinematicBrainStagePanel, complete_stage

failures = 0
BIG = (b"\xff\xd8frame\xff\xd9" * 70000)  # about 700 KB


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.headers.get("Authorization") != "Bearer good-token":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"no token"}')
            return
        if self.path.endswith("/big.mjpeg"):
            self.send_response(200)
            self.send_header("Content-Length", str(len(BIG)))
            self.end_headers()
            self.wfile.write(BIG)
            return
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error":"missing"}')


def run_panels():
    controller = SuiteController()
    panel = KinematicBrainStagePanel(controller)
    half_empty = {"atcRevolver": {"toolCount": None}, "fans": [True], "pumps": "x", "xyTable": {"x": None}}
    state = HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [], "kinematicBrainStage": half_empty}]})
    try:
        controller.active_state_changed.emit(state)
        raised = False
    except Exception as error:
        print(error)
        raised = True
    check("brain panel: a half empty record is drawn", raised, False)
    complete = complete_stage(half_empty)
    check("complete_stage: missing revolver fields read as the seed", complete["atcRevolver"]["toolCount"], 6)
    check("complete_stage: a non-list is replaced", isinstance(complete["pumps"], list), True)
    check("complete_stage: the list given keeps its length", complete["fans"], [True])
    try:
        panel._on_atc_step(1)
        panel._on_fan_toggle(2)
        panel._on_pump_toggle(0)
        panel._on_valve_toggle(9)
        raised = False
    except Exception as error:
        print(error)
        raised = True
    check("brain panel: stepping and toggling beyond the record does not raise", raised, False)

    slot = AtcToolsPanel._slot_count
    check("atc: a grid that is not text", slot(None, {"type": "vertical_panel", "panelGrid": 5}), 4)
    check("atc: a grid with a zero side", slot(None, {"type": "horizontal_panel", "panelGrid": "0x3"}), 1)
    check("atc: slots that are not a number", slot(None, {"type": "revolver", "revolverSlots": "many"}), 8)


def run_xy_table():
    from hydra_suite.ui.panels.xy_table_panel import XYTablePanel

    controller = SuiteController()
    panel = XYTablePanel(controller)
    robot = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle", "hasXYTable": True}
    controller.active_state_changed.emit(HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [robot]}]}))
    buttons = [panel._x_plus_btn, panel._y_plus_btn, panel._width_spin, panel._step_combo]
    check("xy table: no stored table, the jog and size controls are unavailable", [b.isEnabled() for b in buttons], [False] * 4)
    check("xy table: and say why", bool(panel._x_plus_btn.toolTip()), True)
    panel._on_reset()
    check("xy table: after Reset they work", [b.isEnabled() for b in buttons], [True] * 4)


def run_notices():
    check("notices: mixed series without filters", telemetry_notices(False, {}, 5), [("MSG_TELEMETRY_MIXED_SERIES", {})])
    check("notices: no warning with a filter", telemetry_notices(False, {"kind": "temp"}, 5), [])
    check("notices: nothing for an empty answer", telemetry_notices(False, {}, 0), [])
    check("notices: the service limit", telemetry_notices(True, {}, 1000), [("MSG_TELEMETRY_LIMIT_REACHED", {"count": 1000})])


def run_downloads(loop):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=server.server_address[1]))
    conn._token = "good-token"
    folder = tempfile.mkdtemp()
    dest = os.path.join(folder, "big.mjpeg")
    ok = loop.run_until_complete(conn.save_camera_media_to(1, "recordings", "big.mjpeg", dest))
    check("download: a recording is saved", ok, True)
    check("download: the whole body arrived", open(dest, "rb").read() == BIG, True)
    check("download: no partial file is left", os.path.exists(dest + ".part"), False)

    missing = os.path.join(folder, "missing.mjpeg")
    ok = loop.run_until_complete(conn.save_camera_media_to(1, "recordings", "missing.mjpeg", missing))
    check("download: a 404 is a False", ok, False)
    check("download: a 404 writes no file", (os.path.exists(missing), os.path.exists(missing + ".part")), (False, False))

    conn._token = None
    ok = loop.run_until_complete(conn.save_camera_media_to(1, "recordings", "big.mjpeg", os.path.join(folder, "x.mjpeg")))
    check("download: without a session the answer is refused", ok, False)

    conn._token = "good-token"
    ok = loop.run_until_complete(conn.save_camera_media_to(1, "recordings", "big.mjpeg", os.path.join(folder, "nodir", "x.mjpeg")))
    check("download: an unwritable folder is a False", ok, False)
    server.shutdown()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    run_panels()
    run_xy_table()
    run_notices()
    run_downloads(loop)
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
