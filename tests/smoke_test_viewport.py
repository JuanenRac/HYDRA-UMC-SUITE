"""Manual smoke test specifically for the OpenGL viewport - temporarily
sets one robot's model through each of the 3 render families (via direct
API write, restored after) to exercise the actual GL context creation,
shader compile/link, and mesh rendering path for all of them, not just
UR5e: "ur" (UR5e - shared engine, mesh_offsets), "quat" (AR3 - arbitrary
joint axes, quat_family_link_transforms), and "generic" (no STL at all,
render/generic_rig.py's own primitive geometry)."""
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

        test_poses = [
            {"j1": 30, "j2": -60, "j3": 20, "j4": -45, "j5": 10, "j6": 90},
            {"j1": -30, "j2": -30, "j3": 60, "j4": 0, "j5": -20, "j6": 0},
        ]

        for model_name in ("UR5e (6-DOF)", "AR3 (6-DOF)", "Generic (6-DOF)", "xArm6 (6-DOF)", "Lite 6 (6-DOF)", "e.DO (6-DOF)", "Gen3 Lite (6-DOF)", "M-710iC (6-DOF)", "SO-ARM100 (5-DOF)", "Gen2 (6-DOF)", "PiPER (6-DOF)", "Z1 (6-DOF)", "ViperX 300 (6-DOF)", "WidowX 250 (6-DOF)", "Koch v1.1 (5-DOF)", "UR3 (6-DOF)", "UR5 (6-DOF)", "UR10 (6-DOF)"):
            robot.raw["model"] = model_name
            window.controller.push_active_state()
            await asyncio.sleep(0.3)

            # Drive the viewport panel directly rather than through the
            # combo box - QComboBox.setCurrentIndex(0) is a no-op
            # signal-wise when the index is ALREADY 0 (Qt only emits on an
            # actual index change), not what this test is actually trying
            # to exercise (the OpenGL render path itself for each family).
            window.viewport_panel.set_selected_robot(robot)
            await asyncio.sleep(0.3)
            current_widget = window.viewport_panel._stack.currentWidget()
            print(f"[{model_name}] viewport widget:", current_widget.__class__.__name__)
            assert current_widget is window.viewport_panel._viewport, f"viewport did not switch to the real GL widget for {model_name}"

            # Force a couple of paints with different joint poses to
            # exercise the real shader/uniform/draw path for THIS
            # family's own kinematics engine, not just widget construction.
            for pose in test_poses:
                window.viewport_panel._viewport.set_joints_deg(pose)
                app.processEvents()
                await asyncio.sleep(0.2)
            print(f"[{model_name}] GL PAINT PASSES COMPLETED WITHOUT EXCEPTION")

        # restore original model on the server so this test doesn't leave
        # the real settings.json permanently mutated
        robot.raw["model"] = original_model
        window.controller.push_active_state()
        await asyncio.sleep(0.5)
        print("Restored original model:", original_model)

        print("VIEWPORT SMOKE TEST PASSED (ur / quat / generic families)")
        QTimer.singleShot(300, app.quit)

    asyncio.ensure_future(run_scenario())
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
