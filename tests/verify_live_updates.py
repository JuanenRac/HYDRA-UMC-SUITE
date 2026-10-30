# =============================================================================
# HYDRA-UMC SUITE - tests/verify_live_updates.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies how the interface behaves while the server keeps pushing changes:
#   - panel pollers (admin clients, admin logs, cameras, reservations and limits, supervisor) run only
#     while their panel is the one shown
#   - dragging a control writes the settings tree once at once and then once
#     per window, with the latest state, and the last write is sent on close
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import sys
import types

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

import hydra_suite.app as app_module
from hydra_suite.app import SuiteController

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def pump(loop, seconds):
    loop.run_until_complete(asyncio.sleep(seconds))


def run_bridge_gates(loop):
    from qt_suite import SuiteQtBridge

    bridge = SuiteQtBridge(SuiteController())
    gated = bridge._poller_gates()
    states = {key: [t.isActive() for t in timers] for key, timers in gated.items()}
    check("shell: no poller runs on the first panel", any(any(v) for v in states.values()), False)
    for key, timers in gated.items():
        bridge.navigatePanel(key)
        pump(loop, 0.02)
        check(f"shell: {key} pollers run on their panel", [t.isActive() for t in timers], [True] * len(timers))
        others = [t.isActive() for k, ts in gated.items() if k != key for t in ts]
        check(f"shell: the other pollers are stopped while {key} is open", any(others), False)
    bridge.navigatePanel("overview")
    check("shell: all stop when leaving", any(t.isActive() for ts in gated.values() for t in ts), False)
    for timers in gated.values():
        for timer in timers:
            timer.stop()


def run_push_window(loop):
    app_module.PUSH_WINDOW_MS = 80
    controller = SuiteController()
    controller._push_timer.setInterval(80)
    pushes = []

    async def push_state():
        pushes.append(1)

    controller.connections["c"] = types.SimpleNamespace(push_state=push_state, info=types.SimpleNamespace(host="c"), state=None)
    controller._active_id = "c"
    for _ in range(10):
        controller.push_active_state()
    pump(loop, 0.01)
    check("push: the first write goes out at once and the rest wait", len(pushes), 1)
    pump(loop, 0.2)
    check("push: the rest became one write", len(pushes), 2)
    pump(loop, 0.3)
    check("push: nothing more once the changes stop", len(pushes), 2)

    for _ in range(5):
        controller.push_active_state()
    loop.run_until_complete(controller.shutdown())
    check("push: closing sends the write that was waiting", len(pushes) >= 3, True)


def run_state_window(loop):
    app_module.STATE_WINDOW_MS = 60
    controller = SuiteController()
    delivered = []
    controller.active_state_changed.connect(lambda state: delivered.append(state))
    controller._active_id = "c"
    for index in range(10):
        controller._on_state_changed("c", index)
    pump(loop, 0.01)
    check("state: the first change reaches the panels at once and the rest wait", delivered, [0])
    pump(loop, 0.12)
    check("state: the rest became one delivery of the latest state", delivered, [0, 9])
    pump(loop, 0.2)
    check("state: nothing more once the changes stop", delivered, [0, 9])
    controller._on_state_changed("c", 20)
    controller._on_state_changed("other", 21)
    pump(loop, 0.12)
    check("state: a server that is not the active one is ignored", delivered[-1], 20)
    controller._on_state_changed("c", 30)
    controller._on_state_changed("c", 31)
    controller._active_id = "d"
    controller._state_pending = None
    controller._state_timer.stop()
    pump(loop, 0.12)
    check("state: a change that waited is dropped when another server becomes active", 31 in delivered, False)
    app_module.STATE_WINDOW_MS = 0
    delivered.clear()
    controller._active_id = "c"
    controller._on_state_changed("c", 1)
    controller._on_state_changed("c", 2)
    check("state: a window of 0 delivers every change", delivered, [1, 2])
    app_module.STATE_WINDOW_MS = 50

def run_gl_format():
    from PySide6.QtGui import QSurfaceFormat

    from hydra_suite.render.gl_format import default_surface_format

    check("gl: Windows and Linux keep Qt's default", (default_surface_format("win32"), default_surface_format("linux")), (None, None))
    fmt = default_surface_format("darwin")
    check("gl: macOS asks for 3.3 core", (fmt.majorVersion(), fmt.minorVersion(), fmt.profile()), (3, 3, QSurfaceFormat.OpenGLContextProfile.CoreProfile))
    source = open("qt_suite.py", encoding="utf-8").read()
    check("gl: the interface installs it before the application exists", source.index("install_default_surface_format()") < source.index("app = QGuiApplication(sys.argv)"), True)


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    run_bridge_gates(loop)
    run_push_window(loop)
    run_state_window(loop)
    run_gl_format()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
