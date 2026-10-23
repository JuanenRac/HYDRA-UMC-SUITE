# =============================================================================
# HYDRA-UMC SUITE - tests/verify_qml_panels.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Loads the real QML and opens every panel of the navigation, with a fake server connection, and fails on any
# warning or error the QML engine prints (a misspelled property, a missing component, a binding that throws):
#   - every panel of nav_items.py builds without a QML error, in the state with no server and with one
#   - the access bar of the Robot Control panel shows the buttons that apply and presses through to the bridge
#   - the safety limits screen is usable by an administrator and refuses an operator
#   - a notice from a server appears on screen and is dismissed
#   - the application menu, the About window and the Remember choice exist
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import sys
import time

sys.path.insert(0, ".")

import qasync
from PySide6.QtCore import QMetaObject, QObject, QtMsgType, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import qt_suite as qs
from hydra_suite import access
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.nav_items import ALL_DOCK_KEYS
from hydra_suite.net.client import AccessResult, HydraConnection

failures = 0
MESSAGES: list = []


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def handler(kind, context, message):
    if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg) and (".qml" in message or "QML" in message or "qml" in (context.file or "")):
        MESSAGES.append(message)


def settle(loop, rounds=4):
    for _ in range(rounds):
        loop.run_until_complete(asyncio.sleep(0.02))
        QGuiApplication.processEvents()


def find(root, name):
    return root.findChild(QObject, name)


def main():
    qInstallMessageHandler(handler)
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
    check("the QML loads", len(roots) > 0, True)
    if not roots:
        return 1
    root = roots[0]
    settle(loop)

    # --- every panel, first with no server at all ---
    for key in sorted(ALL_DOCK_KEYS):
        bridge.navigatePanel(key)
        settle(loop, 2)
    check("no server: no panel printed a QML warning or error", MESSAGES, [])

    # --- then with a server that has robots and a reservation ---
    conn = HydraConnection(ServerInfo(host="10.0.0.9", port=3000, username="ana", password="pw"))
    conn.login_ok = True
    conn.role = "operator"
    conn.state = HydraState({
        "activeControllerId": "c1", "settings": {},
        "controllers": [{"id": "c1", "robots": [
            {"id": 1, "name": "Parol", "model": "Parol6 (6-DOF)", "role": "Idle", "hasXYTable": True},
            {"id": 2, "name": "Zed", "model": "Z1 (6-DOF)", "role": "Idle"},
        ], "cameras": []}],
    })
    controller.connections["10.0.0.9:3000"] = conn
    controller._active_id = "10.0.0.9:3000"
    controller.active_state_changed.emit(conn.state)
    bridge.selectRobot("1")
    now = time.time() * 1000
    conn.claims = [access.ClaimEntry(2, robot_name="Zed", owner_username="bob", controller_id="x", expires_at=now + 90000)]

    async def refresh(robot_id=None):
        return True

    conn.refresh_access = refresh
    for key in sorted(ALL_DOCK_KEYS):
        bridge.navigatePanel(key)
        settle(loop, 2)
    check("with a server: no panel printed a QML warning or error", MESSAGES, [])

    # --- the access bar ---
    bridge.navigatePanel("robot")
    settle(loop)
    reserve = find(root, "reserveButton")
    check("access bar: the Reserve button is there and visible on a free robot", (reserve is not None, reserve.property("visible") if reserve else None), (True, True))
    check("access bar: Release and Take over are not", (find(root, "releaseButton").property("visible"), find(root, "takeOverButton").property("visible")), (False, False))
    check("access bar: no arming button while the administrator does not require it", find(root, "jogArmButton").property("visible"), False)
    check("access bar: the badge says the robot is free", find(root, "accessBadge").property("text"), bridge.selectedRobotAccess["text"])
    claims_called = []

    async def claim_robot(robot_id, **kwargs):
        claims_called.append(robot_id)
        return AccessResult(True, 200)

    conn.claim_robot = claim_robot
    QMetaObject.invokeMethod(reserve, "click")
    settle(loop)
    check("access bar: pressing Reserve reaches the connection", claims_called, [1])
    QMetaObject.invokeMethod(find(root, "modeSimButton"), "click")
    settle(loop)
    check("access bar: the Sim button sets Sim", bridge.selectedRobotMode, "sim")
    QMetaObject.invokeMethod(find(root, "modeLiveButton"), "click")
    settle(loop)
    check("access bar: and Live puts it back", bridge.selectedRobotMode, "live")
    conn.safety = access.parse_safety_limits({"limits": {"jog": {"armRequired": True}}})
    bridge.changed.emit()
    settle(loop)
    check("access bar: the arming button appears when required", find(root, "jogArmButton").property("visible"), True)
    conn.claims = [access.ClaimEntry(1, robot_name="Parol", owner_username="bob", controller_id="x", expires_at=now + 90000)]
    conn.role = "admin"
    bridge.changed.emit()
    settle(loop)
    check("access bar: an administrator may take over someone else's robot", find(root, "takeOverButton").property("visible"), True)

    # --- the safety limits screen ---
    conn.role = "operator"
    bridge.navigatePanel("safety_limits")
    settle(loop)
    check("safety: an operator does not get the controls", find(root, "armRequiredBox").property("visible"), False)
    conn.role = "admin"
    conn.safety = access.parse_safety_limits({})
    bridge.navigatePanel("robot")
    bridge.navigatePanel("safety_limits")
    bridge.changed.emit()
    settle(loop)
    box = find(root, "armRequiredBox")
    check("safety: an administrator does", box.property("visible"), True)
    puts = []

    async def put_safety_limits(patch):
        puts.append(patch)
        return AccessResult(True, 200, body={})

    conn.put_safety_limits = put_safety_limits
    QMetaObject.invokeMethod(box, "click")
    settle(loop)
    check("safety: touching a field enables Save", find(root, "safetySaveButton").property("enabled"), True)
    QMetaObject.invokeMethod(find(root, "safetySaveButton"), "click")
    settle(loop, 6)
    check("safety: Save sends the form", (len(puts), puts[0]["jog"]["armRequired"]) if puts else None, (1, True))

    # --- notices ---
    controller.connection_error.emit("10.0.0.9:3000", "robot Parol is reserved by bob")
    settle(loop)
    bar = find(root, "noticeBar")
    check("notice: the banner is on screen with the text", (bar.property("visible"), find(root, "noticeText").property("text")), (True, "robot Parol is reserved by bob"))
    QMetaObject.invokeMethod(find(root, "noticeDismiss"), "click")
    settle(loop)
    check("notice: dismissed", bar.property("visible"), False)

    # --- menu and dialogs ---
    check("menu: the application menu button exists", find(root, "appMenuButton") is not None, True)
    check("menu: the About window exists", find(root, "aboutDialog") is not None, True)
    bridge.navigatePanel("servers")
    settle(loop)
    check("servers: the Remember choice exists", find(root, "rememberBox") is not None, True)
    check("servers: and is ticked by default", find(root, "rememberBox").property("checked"), True)

    check("finally: nothing printed a QML warning or error", MESSAGES, [])
    for message in MESSAGES:
        print("QML:", message)
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
