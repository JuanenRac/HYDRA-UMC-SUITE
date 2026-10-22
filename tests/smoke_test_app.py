"""Manual smoke test - launches the real app windowed (not fullscreen) and
connects to localhost:3000, runs for a few seconds, then exits. Confirms
no exceptions during panel construction, OpenGL init, and a real network
connection - not an automated assertion-based test, a "did it crash"
check meant to be run and watched by a human, or piped to a log for
inspection, since headless Qt GUI testing has real limits."""
import asyncio
import os
import sys

import qasync
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.models import ServerInfo
from hydra_suite.ui.main_window import MainWindow
from hydra_suite.ui.theme import apply_theme


CODE = {"value": 0}


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.setMinimumSize(1000, 700)
    window.resize(1400, 900)
    window.show()

    async def run_scenario():
        await asyncio.sleep(0.5)
        info = ServerInfo(host="127.0.0.1", port=3000, hostname="localhost", username=os.environ.get("HYDRA_UMC_USER", ""), password=os.environ.get("HYDRA_UMC_PASSWORD", ""))
        window.controller.add_server(info)
        print("Added server, waiting for connection + state...")
        await asyncio.sleep(2.0)
        conn = window.controller.active_connection
        print("Connection status live:", conn.is_connected if conn else None)
        # A smoke test that cannot tell a failure from a pass is not one: set
        # HYDRA_UMC_USER / HYDRA_UMC_PASSWORD for the server on localhost:3000.
        if conn is None or not conn.is_connected:
            print("SMOKE TEST FAILED - not connected (are HYDRA_UMC_USER and HYDRA_UMC_PASSWORD set?)")
            CODE["value"] = 1
            app.quit()
            return
        state = window.controller.active_state
        active_controller = state.active_controller if state else None
        print("Robots seen:", [r.model for r in active_controller.robots] if active_controller else None)

        # Select first robot to exercise robot_control -> viewport/trajectory wiring
        if active_controller and active_controller.robots:
            window.robot_control._robot_combo.setCurrentIndex(0)
            await asyncio.sleep(0.3)
            print("Selected robot:", window.robot_control._current_robot)
            print("Viewport stack widget:", window.viewport_panel._stack.currentWidget().__class__.__name__)

        if not active_controller or not active_controller.robots:
            print("SMOKE TEST FAILED - the server answered with no robots")
            CODE["value"] = 1
            app.quit()
            return
        print("SMOKE TEST PASSED - connected, robots read")
        QTimer.singleShot(500, app.quit)

    asyncio.ensure_future(run_scenario())

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
    sys.exit(CODE["value"])
