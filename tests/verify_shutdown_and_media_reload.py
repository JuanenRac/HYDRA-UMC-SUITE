# =============================================================================
# HYDRA-UMC SUITE - tests/verify_shutdown_and_media_reload.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Verifies, with fake connections (no network, no server):
#   - HydraConnection.disconnect() finishes even when closing the socket
#     raises something that is not a WebSocket error
#   - SuiteController.shutdown() closes every server even when one fails
#   - closing the window waits for the connections to be closed before the
#     window really closes (the sockets used to be left to a task that the
#     ending loop never ran)
#   - background tasks started through spawn() log their failure instead of
#     leaving "Task exception was never retrieved"
#   - the camera media panel reloads its list when the active server changes
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import logging
import sys
import types

sys.path.insert(0, ".")

import qasync
from PySide6.QtWidgets import QApplication

from hydra_suite.app import SuiteController, spawn
from hydra_suite.models import ServerInfo
from hydra_suite.net.client import HydraConnection

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class ExplodingSocket:
    async def close(self):
        raise RuntimeError("socket already gone")


class LogCatcher(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def run_disconnect(loop):
    conn = HydraConnection(ServerInfo(host="127.0.0.1", port=1))
    conn._ws = ExplodingSocket()
    seen = []
    conn.status_changed.connect(seen.append)
    try:
        loop.run_until_complete(conn.disconnect())
        raised = False
    except Exception:
        raised = True
    check("disconnect: a socket that fails to close does not raise", raised, False)
    check("disconnect: the cleanup still reaches 'disconnected'", seen[-1:] == ["disconnected"], True)


def run_controller_shutdown(loop):
    controller = SuiteController()
    closed = []

    def fake(name, fail):
        async def disconnect():
            if fail:
                raise RuntimeError("stuck")
            closed.append(name)

        return types.SimpleNamespace(disconnect=disconnect, info=types.SimpleNamespace(host=name))

    controller.connections["a"] = fake("a", True)
    controller.connections["b"] = fake("b", False)
    loop.run_until_complete(controller.shutdown())
    check("shutdown: a failing server does not keep the next one open", closed, ["b"])
    return controller


def run_window_close(loop):
    from hydra_suite.ui.main_window import MainWindow

    window = MainWindow()
    done = []

    async def slow_disconnect():
        await asyncio.sleep(0.05)
        done.append("closed")

    window.controller.connections["z"] = types.SimpleNamespace(disconnect=slow_disconnect, info=types.SimpleNamespace(host="z"))
    window.show()
    window.close()
    check("window: the first close request is held back", window.isVisible(), True)
    loop.run_until_complete(asyncio.sleep(0.3))
    check("window: the connections were closed before the window", done, ["closed"])
    check("window: the window closes afterwards", window.isVisible(), False)


def run_spawn(loop):
    handler = LogCatcher()
    logger = logging.getLogger("hydra_suite.app")
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)

    async def boom():
        raise ValueError("odd answer")

    loop.run_until_complete(asyncio.sleep(0))
    task = spawn(boom())
    loop.run_until_complete(asyncio.sleep(0.01))
    check("spawn: the task failed", task.done() and task.exception() is not None, True)
    check("spawn: the failure was logged", any("odd answer" in m for m in handler.messages), True)
    logger.removeHandler(handler)


def run_media_reload(loop):
    from hydra_suite.ui.panels.camera_media_panel import CameraMediaPanel

    controller = SuiteController()
    panel = CameraMediaPanel(controller)  # built with no server at all
    loop.run_until_complete(asyncio.sleep(0))
    check("media: nothing to list before a server exists", panel._items, [])

    async def list_media():
        return 200, {"items": [{"cameraId": 1, "kind": "snapshots", "filename": "a.jpg", "sizeBytes": 1, "capturedAt": "x", "recording": False}]}

    controller.connections["s"] = types.SimpleNamespace(list_camera_media=list_media, info=types.SimpleNamespace(base_url="http://fake"))
    controller._active_id = "s"
    controller.active_connection_changed.emit("s")
    loop.run_until_complete(asyncio.sleep(0.05))
    check("media: the list loads when the active server changes", len(panel._items), 1)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # the test keeps its loop after the window closes
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    run_disconnect(loop)
    run_controller_shutdown(loop)
    run_window_close(loop)
    run_spawn(loop)
    run_media_reload(loop)
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
