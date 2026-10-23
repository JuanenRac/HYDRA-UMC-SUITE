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
#     program really quits (the sockets used to be left to a task that the
#     ending loop never ran)
#   - background tasks started through spawn() log their failure instead of
#     leaving "Task exception was never retrieved"
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import logging
import sys
import types

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

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
    from PySide6.QtGui import QGuiApplication

    import qt_suite as qs

    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    done = []
    quits = []

    async def slow_disconnect():
        await asyncio.sleep(0.05)
        done.append("closed")

    controller.connections["z"] = types.SimpleNamespace(disconnect=slow_disconnect, info=types.SimpleNamespace(host="z"))
    real_quit = QGuiApplication.quit
    QGuiApplication.quit = staticmethod(lambda: quits.append("quit"))
    try:
        check("window: it may not close before the connections are closed", bridge.shutdownDone, False)
        bridge.shutdownAndQuit()
        bridge.shutdownAndQuit()  # asked twice: still one shutdown
        check("window: the first close request does not quit at once", quits, [])
        loop.run_until_complete(asyncio.sleep(0.3))
    finally:
        QGuiApplication.quit = real_quit
    check("window: the connections were closed before quitting", done, ["closed"])
    check("window: it quits afterwards, once", quits, ["quit"])
    check("window: and then lets the window close", bridge.shutdownDone, True)


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


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    run_disconnect(loop)
    run_controller_shutdown(loop)
    run_window_close(loop)
    run_spawn(loop)
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
