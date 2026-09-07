"""Real assertion-based coverage for RobotControlPanel's own play/pause/
stop/tool/valve/pump controls (ui/panels/robot_control.py) - the atomic
per-command counterparts to HYDRA-UMC-STUDIO's own RobotDetail.tsx
transport buttons and I/O tab, added alongside the pre-existing jog/
speed/acceleration controls this panel already had. Headless: a real
QApplication, a real HydraConnection with httpx.AsyncClient.post
monkeypatched (same boundary verify_send_command_debounce.py already
uses) instead of a real network connection - proves the exact command
name and params this panel sends for each control, not just that a
click doesn't crash.
"""
import asyncio
import sys

import httpx
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import HydraConnection
from hydra_suite.ui.panels.robot_control import RobotControlPanel


def _robot(recorded_points: int = 0) -> dict:
    return {
        "id": "1",
        "model": "Parol6",
        "joints": {},
        "playbackState": {"isPlaying": False, "isPaused": False, "speed": 100, "acceleration": 100},
        "tool": "None",
        "valves": [False, False],
        "pumps": [False, False],
        "recordedPoints": [{}] * recorded_points,
    }


def _state(recorded_points: int = 0) -> HydraState:
    controller = {"id": "c1", "robots": [_robot(recorded_points)]}
    return HydraState({"activeControllerId": "c1", "controllers": [controller]})


def _run() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    posts: list[dict] = []

    async def fake_post(self, url, json=None, headers=None, timeout=None):
        posts.append(json)

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                pass

        return _Resp()

    original_post = httpx.AsyncClient.post
    httpx.AsyncClient.post = fake_post

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def pump() -> None:
        # Lets every asyncio.ensure_future() task robot_control.py's own
        # handlers just scheduled actually run - send_robot_command()
        # only schedules the coroutine, it never runs any of it inline
        # (see robot_control.py's own _on_play_clicked comment).
        loop.run_until_complete(asyncio.sleep(0.01))

    try:
        controller = SuiteController()
        conn = HydraConnection(ServerInfo(host="127.0.0.1", port=3000))
        # Bypasses add_server()'s own real asyncio.ensure_future(conn.connect())
        # - this test verifies send_robot_command()'s own real POSTs, not
        # the separate login/discovery flow verify_discovery.py already
        # covers. Still wires conn.state_changed the same way add_server()
        # does, since send_command()'s own optimistic local_mutate fires
        # THAT signal, not active_state_changed directly - without this
        # wire, RobotControlPanel would never see its own optimistic
        # update and every button/label enabled-state assertion below
        # would see stale data.
        controller.connections["c1"] = conn
        controller._active_id = "c1"
        conn.state_changed.connect(lambda state: controller._on_state_changed("c1", state))

        panel = RobotControlPanel(controller)

        # --- no recorded points: Play must stay disabled, matching -----
        # RobotDetail.tsx's own handlePlay() early return.
        conn.state = _state(recorded_points=0)
        controller.active_state_changed.emit(conn.state)
        assert not panel._play_btn.isEnabled(), "Play must be disabled with nothing real to replay"
        print("RobotControlPanel: Play disabled with zero recordedPoints: PASS")

        # --- with recorded points: Play enabled, sends the atomic 'play' command
        conn.state = _state(recorded_points=3)
        controller.active_state_changed.emit(conn.state)
        assert panel._play_btn.isEnabled()
        panel._play_btn.click()
        pump()
        assert len(posts) == 1
        assert posts[0]["command"] == "play"
        assert posts[0]["params"] == {}, f"'play' takes no params, got {posts[0]['params']!r}"
        print("RobotControlPanel Play: real 'play' command, no params: PASS")

        # --- Pause toggles to 'paused': True, then back to False on Continue
        posts.clear()
        panel._pause_btn.click()
        pump()
        assert len(posts) == 1
        assert posts[0]["command"] == "pause"
        assert posts[0]["params"] == {"paused": True}
        print("RobotControlPanel Pause: real 'pause' command with paused=True: PASS")

        posts.clear()
        panel._current_robot.raw["playbackState"]["isPaused"] = True  # mirrors what the real delta would set
        panel._pause_btn.click()
        pump()
        assert posts[0]["params"] == {"paused": False}, "clicking Pause again while paused must send paused=False (Continue)"
        print("RobotControlPanel Continue: real 'pause' command with paused=False: PASS")

        # --- Stop
        posts.clear()
        panel._stop_btn.click()
        pump()
        assert len(posts) == 1
        assert posts[0]["command"] == "stop"
        assert posts[0]["params"] == {}
        print("RobotControlPanel Stop: real 'stop' command, no params: PASS")

        # --- Tool selector
        posts.clear()
        panel._tool_combo.setCurrentText("Drill (BL4260)")
        pump()
        assert len(posts) == 1
        assert posts[0]["command"] == "tool"
        assert posts[0]["params"] == {"tool": "Drill (BL4260)"}
        print("RobotControlPanel tool selector: real 'tool' command: PASS")

        # --- Valve 1 / Valve 2 are independently indexed
        posts.clear()
        panel._valve_btns[0].click()
        pump()
        assert posts[-1]["command"] == "valve"
        assert posts[-1]["params"] == {"index": 0, "state": True}
        panel._valve_btns[1].click()
        pump()
        assert posts[-1]["params"] == {"index": 1, "state": True}
        print("RobotControlPanel valve toggles: real 'valve' command, correct index: PASS")

        # --- Pump 1 / Pump 2 likewise
        posts.clear()
        panel._pump_btns[0].click()
        pump()
        assert posts[-1]["command"] == "pump"
        assert posts[-1]["params"] == {"index": 0, "state": True}
        panel._pump_btns[1].click()
        pump()
        assert posts[-1]["params"] == {"index": 1, "state": True}
        print("RobotControlPanel pump toggles: real 'pump' command, correct index: PASS")

    finally:
        httpx.AsyncClient.post = original_post
        loop.close()


_run()
print()
print("ALL VERIFY_ROBOT_CONTROL_PANEL CHECKS PASSED")
