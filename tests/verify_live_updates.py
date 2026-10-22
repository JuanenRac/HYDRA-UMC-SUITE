# =============================================================================
# HYDRA-UMC SUITE - tests/verify_live_updates.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies how the panels behave while the server keeps pushing changes:
#   - a combo box is rebuilt only when its list changed (an open drop-down is
#     not closed by every delta)
#   - a field being typed in is not overwritten
#   - a call can be debounced or coalesced
#   - panel pollers (admin clients, admin logs, cameras, supervisor) run only
#     while the panel is shown, in the classic window and in the Qt Quick shell
#   - dragging a control writes the settings tree once at once and then once
#     per window, with the latest state, and the last write is sent on close
#   - the ATC slot rows (and the position editor being typed in) survive a
#     refresh that changes nothing they show
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import sys
import types

sys.path.insert(0, ".")

import qasync
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QWidget

import hydra_suite.app as app_module
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState
from hydra_suite.ui.widgets.live_sync import Trailing, set_text_unless_editing, sync_combo

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


def run_combo():
    combo = QComboBox()
    removed = []
    combo.model().rowsRemoved.connect(lambda *a: removed.append(1))
    entries = [("A", 1), ("B", 2), ("C", 3)]
    combo.blockSignals(True)
    index = sync_combo(combo, entries, 2)
    combo.blockSignals(False)
    check("combo: first fill selects the kept entry", (index, combo.currentData()), (1, 2))
    removed.clear()
    sync_combo(combo, entries, 2)
    check("combo: same list is not rebuilt", removed, [])
    sync_combo(combo, entries, 3)
    check("combo: only the selection moves", (removed, combo.currentData()), ([], 3))
    sync_combo(combo, entries + [("D", 4)], 3)
    check("combo: a changed list is rebuilt and keeps the selection", (combo.count(), combo.currentData()), (4, 3))
    sync_combo(combo, [], None)
    check("combo: an empty list empties it", combo.count(), 0)


def run_field():
    class Typing(QLineEdit):
        focused = True

        def hasFocus(self):
            return self.focused

    edit = Typing()
    edit.setText("192.168.0.")
    check("field: not overwritten while typing", (set_text_unless_editing(edit, "10.0.0.1"), edit.text()), (False, "192.168.0."))
    edit.focused = False
    check("field: written when idle", (set_text_unless_editing(edit, "10.0.0.1"), edit.text()), (True, "10.0.0.1"))


def run_trailing(loop):
    calls = []
    debounce = Trailing(lambda v: calls.append(v), 400, restart=True)
    for v in range(5):
        debounce.request(v)
        pump(loop, 0.02)
    check("debounce: nothing ran while requests kept coming", calls, [])
    pump(loop, 0.9)
    check("debounce: one call with the latest value", calls, [4])

    calls.clear()
    coalesce = Trailing(lambda v: calls.append(v), 60, restart=False)
    for v in range(5):
        coalesce.request(v)
        pump(loop, 0.02)
    pump(loop, 0.1)
    check("coalesce: at most one call per interval, latest value", calls[-1], 4)
    check("coalesce: fewer calls than requests", len(calls) < 5, True)
    coalesce.request(9)
    coalesce.flush()
    check("flush: runs the pending call at once", calls[-1], 9)


def run_visibility(loop):
    from hydra_suite.ui.panels.admin_clients_panel import AdminClientsPanel
    from hydra_suite.ui.panels.admin_logs_panel import AdminLogsPanel
    from hydra_suite.ui.panels.cameras_panel import CamerasPanel
    from hydra_suite.ui.panels.system_supervisor_panel import SystemSupervisorPanel

    controller = SuiteController()
    for cls, names in (
        (AdminClientsPanel, ("_timer", "_tick_timer")),
        (AdminLogsPanel, ("_timer",)),
        (CamerasPanel, ("_status_poll_timer",)),
        (SystemSupervisorPanel, ("_timer",)),
    ):
        panel = cls(controller)
        timers = [getattr(panel, n) for n in names]
        check(f"{cls.__name__}: pollers idle while hidden", [t.isActive() for t in timers], [False] * len(timers))
        panel.show()
        check(f"{cls.__name__}: pollers run when shown", [t.isActive() for t in timers], [True] * len(timers))
        panel.hide()
        check(f"{cls.__name__}: pollers stop when hidden", [t.isActive() for t in timers], [False] * len(timers))
        panel.deleteLater()
    pump(loop, 0.05)


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
    for timer in (bridge._admin_clients_timer, bridge._admin_clients_tick_timer, bridge._admin_logs_timer, bridge._camera_status_timer):
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


def run_atc(loop):
    from hydra_suite.ui.panels.atc_tools_panel import AtcToolsPanel

    controller = SuiteController()
    panel = AtcToolsPanel(controller)
    config = {"type": "vertical_panel", "panelGrid": "2x2", "tools": [{"slot": 0, "tool": "None", "pos": {}}]}
    panel._editing_slot = 0
    panel._rebuild_slots(config, True)
    first = panel._slots_container.itemAt(0).widget()
    editor = panel._slot_pos_editors.get(0)
    check("atc: the position editor of the edited slot exists", editor is not None, True)
    panel._rebuild_slots(dict(config), True)
    check("atc: an unchanged refresh keeps the same rows", panel._slots_container.itemAt(0).widget() is first, True)
    check("atc: and the same editor", panel._slot_pos_editors.get(0) is editor, True)
    panel._rebuild_slots({**config, "tools": [{"slot": 0, "tool": "Gripper", "pos": {}}]}, True)
    check("atc: a changed tool rebuilds the rows", panel._slots_container.itemAt(0).widget() is first, False)


def run_gl_format():
    from PySide6.QtGui import QSurfaceFormat

    from hydra_suite.render.gl_format import default_surface_format

    check("gl: Windows and Linux keep Qt's default", (default_surface_format("win32"), default_surface_format("linux")), (None, None))
    fmt = default_surface_format("darwin")
    check("gl: macOS asks for 3.3 core", (fmt.majorVersion(), fmt.minorVersion(), fmt.profile()), (3, 3, QSurfaceFormat.OpenGLContextProfile.CoreProfile))
    check("gl: main.py installs it before the application exists", open("main.py", encoding="utf-8").read().index("install_default_surface_format()") < open("main.py", encoding="utf-8").read().index("app = QApplication(sys.argv)"), True)


def run_knob():
    from hydra_suite.ui.widgets.rotary_knob import RotaryKnob

    class Wheel:
        accepted = None

        def angleDelta(self):
            return types.SimpleNamespace(y=lambda: 120)

        def ignore(self):
            self.accepted = False

        def accept(self):
            self.accepted = True

    class Focused(RotaryKnob):
        focused = False

        def hasFocus(self):
            return self.focused

    knob = Focused(-180.0, 180.0, 0.0)
    emitted = []
    knob.valueChanged.connect(emitted.append)
    event = Wheel()
    knob.wheelEvent(event)
    check("knob: the wheel is ignored until the knob was clicked", (knob.value(), emitted, event.accepted), (0.0, [], False))
    knob.focused = True
    event = Wheel()
    knob.wheelEvent(event)
    check("knob: with focus the wheel turns it", (knob.value() > 0, len(emitted), event.accepted), (True, 1, True))
    knob.setValue(180.0)
    emitted.clear()
    knob.wheelEvent(Wheel())
    check("knob: at the end of the range nothing is sent", emitted, [])


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    run_combo()
    run_field()
    run_trailing(loop)
    run_visibility(loop)
    run_bridge_gates(loop)
    run_push_window(loop)
    run_atc(loop)
    run_gl_format()
    run_knob()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
