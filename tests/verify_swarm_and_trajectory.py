# =============================================================================
# HYDRA-UMC SUITE - tests/verify_swarm_and_trajectory.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The swarm view, the combined mode, the path viewer with its check before Play and the check of versions:
#   - hydra_suite/swarm.py: one row per robot of every server (a server that does not answer keeps a row), the filters
#     and the counts, the ids of a combination (no repeats, never the robot itself, never past the limit)
#   - hydra_suite/trajectory_view.py: a joint outside its range and a swing over the limit are reported, the path is
#     fitted to its view on each plane
#   - hydra_suite/update_check.py: versions of three or four numbers compare as the UPDATER compares them, a manifest of
#     another ecosystem is refused, a failed read is an answer and not a crash, only https is opened
#   - the bridge (suiteBackend.extras): the switches are off until switched on and are kept in the configuration file;
#     the table lists the robots of two servers at once; the combined mode sends the `combine` command only when it is
#     on; Play asks first only when the check is on; Send turns the points into a trajectory of the robot
# Run headless: QT_QPA_PLATFORM=offscreen. No network and no robot: the connections are fakes.
# =============================================================================
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import qasync
from PySide6.QtGui import QGuiApplication

from hydra_suite import i18n, swarm, trajectory_view, update_check
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


# ---- swarm.py -----------------------------------------------------------------------------------------------

robots_a = [
    {"id": 2, "name": "Arm B", "model": "Parol6 (6-DOF)", "online": True, "urtcConnected": True, "playbackState": {"isPlaying": True}, "combinedWith": [3, 3, 2], "recordedPoints": [{}, {}]},
    {"id": 1, "name": "Arm A", "model": "Generic (6-DOF)", "online": True, "enabled": False},
    {"id": 3, "name": "Arm C", "model": "AR4 (6-DOF)", "online": False},
]
servers = [
    swarm.SwarmServer("s1", "Bench", "connected", robots_a, {1: "ana"}, True),
    swarm.SwarmServer("s2", "Shop", "disconnected", [], {}, False),
]
rows = swarm.build_rows(servers)
check("one row per robot and one for the server that does not answer", [(r["server"], r["robotId"]) for r in rows], [("Bench", 1), ("Bench", 2), ("Bench", 3), ("Shop", -1)])
check("the combination has no repeats and not the robot itself", rows[1]["combinedWith"], [3])
check("the robot named in a combination knows who leads it", rows[2]["ledBy"], [2])
check("playing, paused, idle", [swarm.playback_key({"playbackState": {"isPlaying": True}}), swarm.playback_key({"playbackState": {"isPlaying": True, "isPaused": True}}), swarm.playback_key({})], ["playing", "paused", "idle"])
check("live, simulated, offline", [swarm.source_key(r) for r in robots_a], ["live", "simulated", "offline"])
check("the holder of the reservation", rows[0]["holder"], "ana")
check("the filter of robots that answer", [r["robotId"] for r in swarm.filter_rows(rows, "online")], [1, 2])
check("the filter of robots playing", [r["robotId"] for r in swarm.filter_rows(rows, "playing")], [2])
check("the filter of what needs attention (safe mode, offline, held by another account, server down)", [r["robotId"] for r in swarm.filter_rows(rows, "attention", "", "bob")], [1, 3, -1])
check("a robot held by the account itself is not a warning", (swarm.needs_attention({"status": "connected", "source": "live", "enabled": True, "holder": "ana"}, "ana"), swarm.needs_attention({"status": "connected", "source": "live", "enabled": True, "holder": "ana"}, "bob")), (False, True))
check("the text filter looks in the server and the model", [r["robotId"] for r in swarm.filter_rows(rows, "all", "parol")], [2])
summary = swarm.summarize(rows)
check("the counts", (summary["servers"], summary["serversReachable"], summary["robots"], summary["online"], summary["playing"], summary["held"], summary["combined"]), (2, 1, 3, 2, 1, 1, 1))
check("the table is cut at the limit", len(swarm.build_rows(servers, limit=2)), 2)
check("candidates are the other robots that answer", [o["id"] for o in swarm.combine_candidates(robots_a, 1)], [2])
check("switching on adds once", swarm.toggle_combined([3], 5, True, 1), [3, 5])
check("switching on twice adds once", swarm.toggle_combined([3, 5], 5, True, 1), [3, 5])
check("switching off removes", swarm.toggle_combined([3, 5], 3, False, 1), [5])
check("never the robot itself", swarm.toggle_combined([], 1, True, 1), [])
check("never past the limit", swarm.toggle_combined([2, 3], 4, True, 1, limit=2), [2, 3])
check("a damaged list is cleaned", swarm.toggle_combined([2, 2, "x", True, 1, None, 4], 6, True, 1), [2, 4, 6])
check("the file gives the limits", (swarm.MAX_COMBINED, swarm.FILTERS), (8, ("all", "online", "playing", "attention")))
with tempfile.TemporaryDirectory() as folder:
    damaged = Path(folder) / "x.json"
    damaged.write_text("{not json", encoding="utf-8")
    check("a damaged file leaves the built-in limits", swarm.load_settings(damaged)["maxCombined"], 8)
    odd = Path(folder) / "y.json"
    odd.write_text(json.dumps({"maxCombined": -3, "enabledByDefault": "yes", "maxRows": 10}), encoding="utf-8")
    loaded = swarm.load_settings(odd)
    check("values out of range are not used", (loaded["maxCombined"], loaded["enabledByDefault"], loaded["maxRows"]), (8, False, 10))
check("the swarm view is off by default", swarm.SETTINGS["enabledByDefault"], False)

# ---- trajectory_view.py -------------------------------------------------------------------------------------

pts = [{"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0, "x": 0, "y": 0, "z": 100}, {"j1": 10, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0, "x": 30, "y": 40, "z": 100}]
report = trajectory_view.analyze(pts, "Generic (6-DOF)")
check("a clean trajectory", (report["clean"], report["points"], round(report["lengthMm"], 3), report["maxStepDeg"]), (True, 2, 50.0, 10.0))
bad = trajectory_view.analyze([pts[0], {**pts[1], "j1": 400}, pts[0]], "Generic (6-DOF)")
check("a joint outside its range is reported", [i["point"] for i in bad["issues"] if i["kind"] == "limit"], [1])
check("a swing over the limit is reported on both neighbours", [i["point"] for i in bad["issues"] if i["kind"] == "step"], [1, 2])
check("the position comes from the first three joints when the point has none", trajectory_view.position_of("Parol6 (6-DOF)", {"j1": 10, "j2": 20, "j3": 5}) is not None, True)
check("no position for a model with no kinematics and no x, y, z", trajectory_view.position_of("Generic (6-DOF)", {"j1": 1, "j2": 2, "j3": 3}), None)
for plane in trajectory_view.PLANES:
    drawn = trajectory_view.project([(0, 0, 0), (100, 50, 200)], plane, 220, 170, 12)
    check(f"the {plane} view stays in its box", all(12 - 1e-9 <= x <= 208 + 1e-9 and 12 - 1e-9 <= y <= 158 + 1e-9 for x, y in drawn), True)
check("an empty path draws nothing", trajectory_view.project([], "top"), [])

# the orbit view: a path turns around and stays in its box; the turn is bounded
cube = [(0, 0, 0), (100, 0, 0), (100, 100, 0), (0, 100, 0), (0, 0, 100), (100, 100, 100)]
for yaw, pitch in ((0, 0), (35, 25), (-170, 85), (90, -40)):
    drawn = trajectory_view.project_orbit(cube, yaw, pitch, 220, 170, 12)
    check(f"the orbit view at {yaw}, {pitch} stays in its box", all(12 - 1e-9 <= x <= 208 + 1e-9 and 12 - 1e-9 <= y <= 158 + 1e-9 for x, y in drawn), True)
side = trajectory_view.project_orbit([(0, 0, 0), (0, 0, 100)], 0, 0, 220, 170, 12)
check("looking from the side, a vertical line is vertical and goes up", (round(side[0][0]), side[0][1] > side[1][1]), (round(side[1][0]), True))
top = trajectory_view.project_orbit([(0, 0, 0), (100, 0, 0)], 0, 90, 220, 170, 12)
check("looking from straight above, x goes right", top[1][0] > top[0][0], True)
check("an empty path draws nothing in the orbit view", trajectory_view.project_orbit([], 10, 10), [])
check("the turn wraps the yaw", trajectory_view.turn_orbit(170, 0, 1, 0, 15), (-175.0, 0.0))
check("the turn stops the pitch at 85 degrees", trajectory_view.turn_orbit(0, 80, 0, 1, 15), (0.0, 85.0))
check("a number typed with a decimal comma is read", (trajectory_view.parse_millimetres("12,5"), trajectory_view.parse_millimetres(" -3 "), trajectory_view.parse_millimetres("abc"), trajectory_view.parse_millimetres("nan"), trajectory_view.parse_millimetres(None)), (12.5, -3.0, None, None, None))

# moving a point to a typed position
parol = "Parol6 (6-DOF)"
here = trajectory_view.position_of(parol, {"j1": 20, "j2": 10, "j3": 5})
start = {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 1.0, "j5": 2.0, "j6": 3.0, "_time": "10:00:00"}
moved, code, miss = trajectory_view.move_point(parol, start, here, 5.0)
check("a reachable position is taken", (code, moved is not None, miss < 1.0), ("ok", True, True))
check("the other joints and fields stay", (moved["j4"], moved["j5"], moved["j6"], moved["_time"]), (1.0, 2.0, 3.0, "10:00:00"))
check("the point now stands where it was asked", max(abs(a - b) for a, b in zip((moved["x"], moved["y"], moved["z"]), here)) < 1.0, True)
check("the point that was given is not changed", start["j1"], 0.0)
far = trajectory_view.move_point(parol, start, (9000.0, 9000.0, 9000.0), 5.0)
check("a position out of reach is refused and says how far it stays", (far[0], far[1], far[2] > 5.0), (None, "unreachable", True))
check("a model with no kinematics here is refused", trajectory_view.move_point("Generic (6-DOF)", start, (1.0, 2.0, 3.0), 5.0)[1], "no_kinematics")
check("a position that is not a number is refused", trajectory_view.move_point(parol, start, (float("nan"), 0.0, 0.0), 5.0)[1], "invalid")
check("the preview before Play is off by default", trajectory_view.SETTINGS["previewBeforePlayByDefault"], False)

# ---- update_check.py ----------------------------------------------------------------------------------------

check("0.8.0 equals 0.8.0.0", update_check.compare("0.8.0", "0.8.0.0"), "current")
check("a fourth number counts", update_check.compare("0.8.0.9", "0.8.1.0"), "outdated")
check("ahead of the published one", update_check.compare("0.9.0", "0.8.1.0"), "ahead")
check("not a version", update_check.compare("v1", "0.8.0"), "unknown")
check("the address of a manifest", update_check.manifest_url("HYDRA-UMC-SUITE"), "https://raw.githubusercontent.com/JuanenRac/HYDRA-UMC-SUITE/main/hydra-umc.project.json")
manifest = json.dumps({"ecosystem": "HYDRA-UMC", "name": "HYDRA-UMC-SUITE", "version": "0.9.0"})
check("the version of a manifest", update_check.manifest_version(manifest, "HYDRA-UMC-SUITE"), "0.9.0")
check("a manifest of another ecosystem is refused", update_check.manifest_version(json.dumps({"ecosystem": "ARMOR", "name": "X", "version": "1.0.0"})), None)
check("a manifest of another project is refused", update_check.manifest_version(manifest, "HYDRA-UMC-SERVER"), None)
check("api states", [update_check.api_state(2, 2), update_check.api_state(1, 2), update_check.api_state(0, 2), update_check.api_state("x", 2)], ["ok", "too_old", "unknown", "unknown"])

asked: list[str] = []


def fake_fetch(url: str, timeout: float) -> str:
    asked.append(url)
    if "SUITE" in url:
        return manifest
    return json.dumps({"ecosystem": "HYDRA-UMC", "name": "HYDRA-UMC-SERVER", "version": "0.8.2.0"})


result = update_check.run_check("0.7.8", [{"name": "Bench", "appVersion": "0.8.1.0", "remoteApiVersion": 2}, {"name": "Old", "appVersion": "0.8.2.0", "remoteApiVersion": 1}], fake_fetch)
check("this program is behind", result["suite"]["state"], "outdated")
check("the servers are compared with the newest server", [s["state"] for s in result["servers"]], ["outdated", "current"])
check("the old API is flagged", [s["api"] for s in result["servers"]], ["ok", "too_old"])
check("the two manifests are read once each", len(asked), 2)
check("no server, no read of the server manifest", len(update_check.run_check("0.7.8", [], fake_fetch)["servers"]), 0)


def failing_fetch(url: str, timeout: float) -> str:
    raise OSError("no network")


failed = update_check.run_check("0.7.8", [{"name": "A", "appVersion": "0.8.0", "remoteApiVersion": 2}], failing_fetch)
check("a failed read is unknown, with the reason", (failed["suite"]["state"], failed["servers"][0]["state"], len(failed["errors"])), ("unknown", "unknown", 2))
try:
    update_check.fetch_text("file:///etc/passwd", 1.0)
    check("only https is opened", "opened", "refused")
except ValueError:
    check("only https is opened", "refused", "refused")
check("the check of versions is off by default", update_check.SETTINGS["enabledByDefault"], False)

# the real read, against a small web server on this machine (the manifests of both repositories)
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ManifestPage(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        name = self.path.split("/")[2] if self.path.count("/") >= 3 else ""
        body = json.dumps({"ecosystem": "HYDRA-UMC", "name": name, "version": "9.9.9" if name.endswith("SUITE") else "0.8.2.0"}).encode()
        self.send_response(200 if name else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silent
        pass


httpd = ThreadingHTTPServer(("127.0.0.1", 0), ManifestPage)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
local = {**update_check.SETTINGS, "rawBase": f"http://127.0.0.1:{httpd.server_address[1]}"}
real = update_check.run_check("0.7.8", [{"name": "Bench", "appVersion": "0.8.2.0", "remoteApiVersion": 2}], settings=local)
httpd.shutdown()
check("a real read of the manifests from a local server", (real["suite"]["latest"], real["suite"]["state"], real["servers"][0]["latest"], real["servers"][0]["state"], real["errors"]), ("9.9.9", "outdated", "0.8.2.0", "current", []))

# ---- the bridge ---------------------------------------------------------------------------------------------


def bridge_checks() -> None:
    import qt_suite as qs

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    for timer in (bridge._admin_clients_timer, bridge._admin_logs_timer, bridge._camera_status_timer):
        timer.stop()
    extras = bridge.extras

    check("the switches are off until switched on", (extras.swarmEnabled, extras.combinedModeEnabled, extras.previewEnabled, extras.updatesEnabled), (False, False, False, False))
    check("nothing is listed while the swarm view is off", (extras.swarmRows, extras.swarmSummary), ([], ""))
    extras.setSwarmEnabled(True)
    extras.setPreviewEnabled(True)
    saved = i18n.load_config()
    check("the switches are kept in the configuration file", (saved.get("swarm_view"), saved.get("trajectory_preview"), saved.get("combined_mode")), (True, True, None))

    bridge.addManualServer("10.0.0.1", 3000, "ana", "pw", False)
    bridge.addManualServer("10.0.0.2", 3000, "ana", "pw", False)
    ids = [row["connId"] for row in bridge.serverRows]
    for conn_id, name, base in ((ids[0], "Bench", 0), (ids[1], "Shop", 10)):
        conn = controller.connections[conn_id]
        conn.state = HydraState({
            "settings": {}, "activeControllerId": "c1",
            "controllers": [{"id": "c1", "name": name, "robots": [
                {"id": base + 1, "name": f"{name} 1", "model": "Parol6 (6-DOF)", "online": True, "urtcConnected": True, "joints": {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0}},
                {"id": base + 2, "name": f"{name} 2", "model": "Parol6 (6-DOF)", "online": True},
            ]}],
        })
    controller.set_active(ids[0])
    controller.active_state_changed.emit(controller.connections[ids[0]].state)
    table = extras.swarmRows
    check("the table lists the robots of two servers at once", sorted((r["server"], r["robotId"]) for r in table), sorted([(controller.connections[ids[0]].info.display_name, 1), (controller.connections[ids[0]].info.display_name, 2), (controller.connections[ids[1]].info.display_name, 11), (controller.connections[ids[1]].info.display_name, 12)]))
    check("the summary counts them", "4 " in extras.swarmSummary or "4," in extras.swarmSummary, True)
    extras.setSwarmFilter("playing")
    check("a filter with no match lists nothing", extras.swarmRows, [])
    extras.setSwarmFilter("all")
    extras.swarmOpen(ids[1], 11)
    check("opening a row makes its server active and selects its robot", (controller._active_id, bridge.selectedRobotId), (ids[1], "11"))

    # combined mode: off, nothing is sent; on, the `combine` command goes out with the list
    sent: list = []
    def fake_send(robot_id, command, params=None, mutate=None, debounce_ms=0):
        sent.append((robot_id, command, params))
        if mutate is not None:  # the optimistic change that the real command makes at once
            mutate(bridge._selected_robot())

    controller.send_robot_command = fake_send
    controller.active_state_changed.emit(controller.connections[ids[1]].state)
    bridge._select_robot("11")
    extras.toggleCombine(12, True)
    check("with the mode off nothing is sent", sent, [])
    check("the status says there is no combination", extras.combinedStatus, i18n._("COMBINE_NONE"))
    extras.setCombinedModeEnabled(True)
    check("the other robot is offered", [o["id"] for o in extras.combineOptions], [12])
    conn = controller.active_connection
    conn.has_edit_commands = True
    extras.toggleCombine(12, True)
    check("the combine command goes out with the list", sent, [("11", "combine", {"with": [12]})])
    check("the status names the robot it is combined with", "Shop 2" in extras.combinedStatus or "#12" in extras.combinedStatus, True)
    sent.clear()
    extras.toggleCombine(12, True)
    check("the same robot twice sends nothing", sent, [])

    # Play and Send
    played: list = []
    bridge.playSelectedRobot = lambda: played.append(True)
    asked_dialog: list = []
    extras.previewRequested.connect(lambda: asked_dialog.append(extras.pendingKind))
    robot = bridge._selected_robot()
    robot.raw["recordedPoints"] = [{"motionType": "model-joints", "j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0, "x": 0, "y": 0, "z": 0}, {"motionType": "model-joints", "j1": 300, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0, "x": 10, "y": 0, "z": 0}]
    extras.requestPlay()
    check("with the check on, Play asks first and shows the problems", (played, asked_dialog, extras.pendingKind, extras.pendingPreview["clean"] is False, extras.pendingPreview["count"] > 0), ([], ["play"], "play", True, True))
    extras.cancelPreview()
    check("cancelling plays nothing", (played, extras.pendingKind), ([], ""))
    extras.requestPlay()
    extras.confirmPreview()
    check("confirming plays", played, [True])
    extras.setPreviewEnabled(False)
    played.clear()
    extras.requestPlay()
    check("with the check off, Play goes straight through", (played, extras.pendingKind), ([True], ""))

    bridge._trajectory_points = [{"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0, "_time": "10:00:00"}, {"j1": 10.0, "j2": 5.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0, "_time": "10:00:01"}]
    bridge._trajectoryChanged.emit()
    view = extras.trajectoryView
    check("the viewer draws three planes and the orbit view", [p["plane"] for p in view["paths"]], ["top", "side", "front", "orbit"])
    extras.rotateTrajectoryOrbit(1, 0)
    check("the orbit view turns one step and says its angles", "50" in extras.trajectoryView["paths"][3]["label"], True)
    reachable = trajectory_view.position_of("Parol6 (6-DOF)", {"j1": 20, "j2": 10, "j3": 5})
    shown = extras.trajectoryPointPosition(0)
    check("the position of a point is offered for the fields", set(shown), {"x", "y", "z"})
    extras.setTrajectoryPointPosition(0, f"{reachable[0]:.2f}".replace(".", ","), f"{reachable[1]:.2f}", f"{reachable[2]:.2f}")
    check("a point is moved to a typed position", abs(bridge._trajectory_points[0]["j1"] - 20) < 2.0, True)
    check("and the notice says so", "moved to" in bridge._notice_text or "mm" in bridge._notice_text, True)
    before = dict(bridge._trajectory_points[0])
    extras.setTrajectoryPointPosition(0, "9000", "9000", "9000")
    check("a position out of reach leaves the point as it was and says why", (bridge._trajectory_points[0] == before, bridge._notice_severity), (True, "warn"))
    extras.setTrajectoryPointPosition(0, "x", "1", "2")
    check("text that is not a number changes nothing", bridge._trajectory_points[0] == before, True)
    bridge._trajectory_points[0] = {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0, "_time": "10:00:00"}
    extras.moveTrajectoryPoint(0, 1)
    check("a point moves down", [p["j1"] for p in bridge._trajectory_points], [10.0, 0.0])
    extras.duplicateTrajectoryPoint(0)
    check("a point is duplicated", len(bridge._trajectory_points), 3)
    bridge._trajectory_points.pop(1)
    sent.clear()
    extras.requestSend()
    check("with the check off, Send goes out as the trajectory of the robot", (sent[0][0], sent[0][1], len(sent[0][2]["points"]), sent[0][2]["points"][0]["motionType"], "x" in sent[0][2]["points"][0]), ("11", "points", 2, "model-joints", True))

    # check of versions: nothing is read while the switch is off
    extras.checkUpdates()
    check("the check of versions does nothing while it is off", extras.updateBusy, False)
    loop.close()


if __name__ == "__main__":
    folder = tempfile.mkdtemp(prefix="suite_extras_")
    i18n.CONFIG_FILE_PATH = Path(folder) / "hydra_suite_config.json"  # the real configuration file is never touched
    bridge_checks()
    if failures:
        print(f"verify_swarm_and_trajectory: {failures} FAILED")
        sys.exit(1)
    print("verify_swarm_and_trajectory: OK")
