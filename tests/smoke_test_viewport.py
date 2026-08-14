"""Manual smoke test specifically for the OpenGL viewport - temporarily
sets one robot's model to UR5e (via direct API write, restored after) to
exercise the actual GL context creation, shader compile/link, and mesh
rendering path, the highest-risk least-tested part of this app."""
import asyncio
import sys

import qasync
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.models import ServerInfo
from hydra_suite.ui.main_window import MainWindow
from hydra_suite.ui.theme import apply_theme


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.resize(1400, 900)
    window.show()

    async def run_scenario():
        await asyncio.sleep(0.5)
        info = ServerInfo(host="127.0.0.1", port=3000, hostname="localhost")
        window.controller.add_server(info)
        await asyncio.sleep(1.5)

        state = window.controller.active_state
        active = state.active_controller
        robot = active.robots[0]
        original_model = robot.raw.get("model")
        print("Original model:", original_model)
        robot.raw["model"] = "UR5e (6-DOF)"
        window.controller.push_active_state()
        await asyncio.sleep(0.5)

        # Drive the viewport panel directly rather than through the combo
        # box - QComboBox.setCurrentIndex(0) is a no-op signal-wise when
        # the index is ALREADY 0 (Qt only emits on an actual index change),
        # which this scenario's own robot[0] already was before the model
        # mutation below - not what this test is actually trying to
        # exercise (the OpenGL render path itself).
        window.viewport_panel.set_selected_robot(robot)
        await asyncio.sleep(0.3)
        current_widget = window.viewport_panel._stack.currentWidget()
        print("Viewport current widget after UR5e select:", current_widget.__class__.__name__)
        assert current_widget is window.viewport_panel._viewport, "viewport did not switch to the real GL widget for UR5e"

        # Force a couple of paints with different joint poses to exercise
        # the real shader/uniform/draw path, not just widget construction.
        window.viewport_panel._viewport.set_joints_deg({"j1": 30, "j2": -60, "j3": 20, "j4": -45, "j5": 10, "j6": 90})
        app.processEvents()
        await asyncio.sleep(0.2)
        window.viewport_panel._viewport.set_joints_deg({"j1": -30, "j2": -30, "j3": 60, "j4": 0, "j5": -20, "j6": 0})
        app.processEvents()
        await asyncio.sleep(0.2)
        print("GL PAINT PASSES COMPLETED WITHOUT EXCEPTION")

        # restore original model on the server so this test doesn't leave
        # the real settings.json permanently mutated
        robot.raw["model"] = original_model
        window.controller.push_active_state()
        await asyncio.sleep(0.5)
        print("Restored original model:", original_model)

        print("VIEWPORT SMOKE TEST PASSED")
        QTimer.singleShot(300, app.quit)

    asyncio.ensure_future(run_scenario())
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
