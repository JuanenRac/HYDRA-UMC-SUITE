"""Manual smoke test for the new CamerasPanel - launches the real app,
connects to the real local server, and confirms real camera metadata
(not a placeholder) rendered into camera cards, then round-trips a
toggle (connect/disconnect) through the real server and back, verifying
the change is genuinely persisted (not just local UI state)."""
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
        cameras = active.cameras
        print(f"Real cameras from server: {len(cameras)}")
        for cam in cameras:
            print(" ", cam)
        assert len(cameras) > 0, "expected at least one real camera from the server"

        app.processEvents()
        card_count = len(window.cameras_panel._cards)
        print(f"CamerasPanel built {card_count} camera cards")
        assert card_count == len(cameras), "card count must match real camera count"

        # Round-trip test: flip the first camera's own connected state,
        # push to the real server, re-fetch, confirm the change survived
        # (not just local UI state) - then restore original value.
        first = cameras[0]
        original = first.connected
        print(f"Toggling camera {first.id} connected: {original} -> {not original}")
        window.cameras_panel._on_toggle_connection(first.id)
        await asyncio.sleep(0.5)

        await window.controller.active_connection.fetch_state()
        await asyncio.sleep(0.3)
        refetched = window.controller.active_state.active_controller.cameras[0]
        print(f"Re-fetched from server: connected={refetched.connected}")
        assert refetched.connected == (not original), "toggle did not persist to the real server"

        # restore
        window.cameras_panel._on_toggle_connection(first.id)
        await asyncio.sleep(0.5)
        print("Restored original state")

        print("CAMERAS SMOKE TEST PASSED - real metadata, real round-trip")
        QTimer.singleShot(300, app.quit)

    asyncio.ensure_future(run_scenario())
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
