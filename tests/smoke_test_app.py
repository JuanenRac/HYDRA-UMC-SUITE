"""Manual smoke test - launches the real app windowed (not fullscreen) and
connects to localhost:3000, runs for a few seconds, then exits. Confirms
no exceptions during panel construction, OpenGL init, and a real network
connection - not an automated assertion-based test, a "did it crash"
check meant to be run and watched by a human, or piped to a log for
inspection, since headless Qt GUI testing has real limits."""
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
    window.setMinimumSize(1000, 700)
    window.resize(1400, 900)
    window.show()

    async def run_scenario():
        await asyncio.sleep(0.5)
        info = ServerInfo(host="127.0.0.1", port=3000, hostname="localhost")
        window.controller.add_server(info)
        print("Added server, waiting for connection + state...")
        await asyncio.sleep(2.0)
        conn = window.controller.active_connection
        print("Connection status live:", conn.is_connected if conn else None)
        state = window.controller.active_state
        active_controller = state.active_controller if state else None
        print("Robots seen:", [r.model for r in active_controller.robots] if active_controller else None)

        # Select first robot to exercise robot_control -> viewport/trajectory wiring
        if active_controller and active_controller.robots:
            window.robot_control._robot_combo.setCurrentIndex(0)
            await asyncio.sleep(0.3)
            print("Selected robot:", window.robot_control._current_robot)
            print("Viewport stack widget:", window.viewport_panel._stack.currentWidget().__class__.__name__)

        print("SMOKE TEST PASSED - no exceptions raised")
        QTimer.singleShot(500, app.quit)

    asyncio.ensure_future(run_scenario())

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
