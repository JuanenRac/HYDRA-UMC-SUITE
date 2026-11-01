# =============================================================================
# HYDRA-UMC SUITE - tests/verify_robot_edits.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The edits of a robot as commands (robot_edits.py): the plan that says which commands carry what a panel changed,
# and the XY table screen of the bridge sending them (xyTableConfig) instead of the whole settings tree, with the
# tree as the way back for a server that predates the commands. Headless; the commands are caught before the network.
# =============================================================================
import asyncio
import sys

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

import qt_suite as qs
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import HydraConnection
from hydra_suite.robot_edits import EDIT_COMMANDS, plan_robot_edits

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def planning() -> None:
    robot = {"id": 1, "hasXYTable": False, "xyTable": {"pos": {"x": 5, "y": 6}, "tableSize": {"width": 500, "length": 500}}, "playbackState": {"isPlaying": False, "isLooping": False, "speed": 100}}
    check("plan: the commands are the ones the server knows", sorted(EDIT_COMMANDS), sorted(["points", "loop", "model", "role", "combine", "joints", "xyTableConfig"]))
    check("plan: recorded points are one command with the whole list", plan_robot_edits(robot, {"recordedPoints": [{"j1": 1}]}).commands, [("points", {"points": [{"j1": 1}]})])
    check("plan: a model, a role, a combination", [c for c, _ in plan_robot_edits(robot, {"model": "AR4 (6-DOF)", "role": "CNC", "combinedWith": [2, 3]}).commands], ["model", "role", "combine"])
    check("plan: a combination with something that is not a number is left to the tree", plan_robot_edits(robot, {"combinedWith": ["a"]}).rest, ["combinedWith"])
    check("plan: an empty model is left to the tree", plan_robot_edits(robot, {"model": "  "}).rest, ["model"])
    check("plan: only the loop flag of the playback is a command", plan_robot_edits(robot, {"playbackState": {**robot["playbackState"], "isLooping": True}}).commands, [("loop", {"value": True})])
    check("plan: any other change of the playback stays in the tree", plan_robot_edits(robot, {"playbackState": {**robot["playbackState"], "speed": 50}}).rest, ["playbackState"])
    check("plan: nothing changed in the playback, nothing to send", plan_robot_edits(robot, {"playbackState": dict(robot["playbackState"])}).commands, [])
    check("plan: the flag of the table is one command", plan_robot_edits(robot, {"hasXYTable": True}).commands, [("xyTableConfig", {"enabled": True})])
    resized = {**robot["xyTable"], "tableSize": {"width": 800, "length": 500}}
    check("plan: the size of the table is the same command", plan_robot_edits(robot, {"xyTable": resized}).commands, [("xyTableConfig", {"tableSize": {"width": 800, "length": 500}})])
    check("plan: the flag and the size go in one command", plan_robot_edits(robot, {"hasXYTable": True, "xyTable": resized}).commands, [("xyTableConfig", {"enabled": True, "tableSize": {"width": 800, "length": 500}})])
    moved = {**robot["xyTable"], "pos": {"x": 0, "y": 0}}
    check("plan: the position of the table is not part of its layout and stays in the tree", plan_robot_edits(robot, {"xyTable": moved}).rest, ["xyTable"])
    check("plan: joints only when asked for", (plan_robot_edits(robot, {"joints": {"j1": 1}}).rest, plan_robot_edits(robot, {"joints": {"j1": 1}}, joints=True).commands), (["joints"], [("joints", {"joints": {"j1": 1}})]))
    check("plan: anything else is the tree's", plan_robot_edits(robot, {"jogStep": 2}).rest, ["jogStep"])
    check("plan: no robot yet is the same as an empty one", plan_robot_edits(None, {"hasXYTable": True}).commands, [("xyTableConfig", {"enabled": True})])


def screen() -> None:
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    for timers in bridge._poller_gates().values():
        for timer in timers:
            timer.stop()
    bridge._scheduler_timer.stop()
    conn = HydraConnection(ServerInfo(host="10.0.0.9", port=3000, username="ana", password="pw"))
    conn.login_ok = True
    conn.role = "admin"
    conn.state = HydraState({
        "activeControllerId": "c1",
        "settings": {},
        "controllers": [{"id": "c1", "robots": [{"id": 1, "name": "Parol", "model": "Parol6 (6-DOF)", "role": "Idle", "hasXYTable": False}]}],
    })
    controller.connections["10.0.0.9:3000"] = conn
    controller._active_id = "10.0.0.9:3000"
    controller.active_state_changed.emit(conn.state)

    sent: list[tuple] = []
    pushed: list[int] = []
    controller.send_robot_command = lambda robot_id, command, params=None, local_mutate=None, debounce_ms=0: (sent.append((str(robot_id), command, params)), local_mutate(conn.state.active_controller.robot_by_id(str(robot_id))) if local_mutate else None)
    controller.push_active_state = lambda: pushed.append(1)

    bridge._xy_robots_cache = list(conn.state.active_controller.robots)
    bridge._xy_selected_robot_id = "1"
    bridge.enableXyTable()
    check("screen: enabling the table sends the command and not the tree", (sent, pushed), ([("1", "xyTableConfig", {"enabled": True})], []))
    check("screen: and the table shows as enabled at once", conn.state.active_controller.robot_by_id("1").has_xy_table, True)

    sent.clear()
    bridge.resetXyTable()
    check("screen: resetting writes the layout through the command", [c for _, c, _ in sent], ["xyTableConfig"] if sent else [])
    robot = conn.state.active_controller.robot_by_id("1")
    sent.clear()
    pushed.clear()
    bridge.setXyWidth(900)
    check("screen: a width goes as the size of the table", (sent[0][1], sent[0][2]["tableSize"]["width"], pushed), ("xyTableConfig", 900, []))
    check("screen: the screen shows the new width", robot.xy_table["tableSize"]["width"], 900)

    conn.has_edit_commands = False
    sent.clear()
    bridge.setXyLength(700)
    check("screen: a server that predates the commands gets the whole tree as before", (sent, pushed), ([], [1]))
    check("screen: and the change is in the local state", robot.xy_table["tableSize"]["length"], 700)


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    planning()
    screen()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
