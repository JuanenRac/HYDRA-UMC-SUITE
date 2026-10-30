# =============================================================================
# HYDRA-UMC SUITE - tools/make_screenshots.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Takes the screenshots of the README: the real Qt Quick interface, without a window on the desktop (the offscreen Qt platform and the software
# renderer), with a made-up server connection that has made-up robots. Nothing real is behind the pictures, and nothing is sent to any network.
#
#   python tools/make_screenshots.py              writes images/screenshots/<name>.png at 1920x1080
#   python tools/make_screenshots.py --out DIR    writes them in DIR instead, to look at them before they replace the ones in the repository
#
# It takes no mouse or keyboard of the desktop. The 3D views need OpenGL, which the offscreen platform cannot give, so the screens that are only
# a 3D view are not in the set (nor the ones that need a live server). Run it from the repository root, with the interpreter of the project (the one that has PySide6).
# =============================================================================
import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))   # the offscreen platform finds no fonts by itself
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import qasync  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

import qt_suite as qs  # noqa: E402
from hydra_suite import access  # noqa: E402
from hydra_suite.app import SuiteController  # noqa: E402
from hydra_suite.models import HydraState, ServerInfo  # noqa: E402
from hydra_suite.net.client import HydraConnection  # noqa: E402

# the screens: (file, panel key)
SCREENS = [
    ("overview", "overview"),
    ("robot-control", "robot"),
    ("flasher-studio", "urtc_flasher"),
    ("tester-center", "urtc_tester"),
    ("safety-limits", "safety_limits"),
]

MODELS = [("Robot A1", "PAROL6 (6-DOF)", "PnP"), ("Robot A2", "FAZE4 (6-DOF)", "CNC"), ("Robot A3", "PAROL6 (6-DOF)", "Inspection"), ("Robot A4", "FAZE4 (6-DOF)", "Idle")]


def settle(loop, rounds=6):
    for _ in range(rounds):
        loop.run_until_complete(asyncio.sleep(0.05))
        QGuiApplication.processEvents()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "images" / "screenshots"))
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    QQuickStyle.setStyle("Basic")
    access.reset_controller_id("suite-here")
    qs.save_config = lambda updates: True
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller, frame_provider=qs.CameraFrameProvider(), viewport_frame_provider=qs.ViewportFrameProvider(), media_frame_provider=qs.MediaFrameProvider(), catalog_frame_provider=qs.ViewportFrameProvider())
    for timers in bridge._poller_gates().values():
        for timer in timers:
            timer.stop()
    engine = QQmlApplicationEngine()
    engine.addImageProvider("cameraFrames", bridge._frame_provider)
    engine.addImageProvider("viewportFrame", bridge._viewport_frame_provider)
    engine.addImageProvider("vacuumFrame", bridge._vacuum_frame_provider)
    engine.addImageProvider("cameraMedia", bridge._media_frame_provider)
    engine.addImageProvider("catalogFrame", bridge._catalog_frame_provider)
    engine.rootContext().setContextProperty("suiteBackend", bridge)
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(qs.QML_PATH)))
    roots = engine.rootObjects()
    if not roots:
        print("SCREENSHOTS=FAIL the interface did not load")
        return 1
    root = roots[0]
    root.setProperty("width", 1920)
    root.setProperty("height", 1080)
    root.show()

    conn = HydraConnection(ServerInfo(host="192.0.2.10", port=3000, username="admin", password="example"))
    conn.login_ok = True
    conn.role = "admin"
    robots = [{"id": index + 1, "name": name, "model": model, "role": role, "hasXYTable": index == 0} for index, (name, model, role) in enumerate(MODELS)]
    conn.state = HydraState({"activeControllerId": "c1", "settings": {}, "controllers": [{"id": "c1", "robots": robots, "cameras": []}]})
    controller.connections["192.0.2.10:3000"] = conn
    controller._active_id = "192.0.2.10:3000"
    controller.active_state_changed.emit(conn.state)
    bridge.selectRobot("1")
    conn.safety = access.parse_safety_limits({})

    async def refresh(robot_id=None, claims=True):
        return True

    conn.refresh_access = refresh
    settle(loop)
    for name, key in SCREENS:
        bridge.navigatePanel(key)
        settle(loop, 12)
        image = root.grabWindow()
        path = out / f"{name}.png"
        image.save(str(path))
        print("wrote", path, image.width(), "x", image.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
