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
from hydra_suite.i18n import _
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

    async def refresh(robot_id=None, claims=True):
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

    # --- the audit record screen ---
    conn.role = "operator"
    bridge.navigatePanel("audit_record")
    settle(loop)
    check("audit: an operator does not get the controls", find(root, "auditVerifyButton").property("visible"), False)
    conn.role = "admin"
    fetched = []
    lines = []
    previous = "0" * 64
    for seq in (1, 2):
        body = {"seq": seq, "ts": f"2030-01-01T00:00:0{seq}.000Z", "type": "claim", "outcome": "ok", "username": "ana", "controllerId": "w1", "ip": "10.0.0.5", "robotId": 1, "detail": {"ttlMs": 60000}, "prev": previous}
        import hashlib
        import json as _json
        digest = hashlib.sha256(_json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        lines.append({**body, "hash": digest})
        previous = digest

    async def fetch_audit(limit=None, type=None, robot_id=None, verify=False):
        fetched.append((limit, type, robot_id, verify))
        body = {"enabled": True, "entries": lines}
        if verify:
            body["verification"] = {"ok": True, "entries": 2}
        return AccessResult(True, 200, body=body), access.parse_audit(body)

    conn.fetch_audit = fetch_audit
    bridge.navigatePanel("robot")
    bridge.navigatePanel("audit_record")
    settle(loop, 6)
    check("audit: opening the screen reads the record", fetched[:1], [(100, None, None, False)])
    check("audit: the screen has the controls for an administrator", (find(root, "auditVerifyButton").property("visible"), find(root, "auditList") is not None), (True, True))
    check("audit: the newest line comes first", [row["seq"] for row in bridge.auditRows], [2, 1])
    QMetaObject.invokeMethod(find(root, "auditVerifyButton"), "click")
    settle(loop, 6)
    check("audit: Verify asks the server to verify", fetched[-1][3], True)
    check("audit: and both chain checks pass", [line["ok"] for line in bridge.auditChain], [True, True])
    bridge.setAuditType("release")
    settle(loop, 6)
    check("audit: the filter goes to the server", fetched[-1][:2], (100, "release"))
    bridge.setAuditType("")
    bridge.setAuditLimit(250)
    settle(loop, 6)
    check("audit: and so does the number of lines", fetched[-1][0], 250)
    bridge.setAuditLimit(7)
    check("audit: a number that is not offered changes nothing", bridge.auditLimit, 250)
    bridge.setAuditLimit(100)
    settle(loop, 4)

    # --- the user accounts screen ---
    conn.role = "operator"
    bridge.navigatePanel("users")
    settle(loop)
    check("users: an operator does not get the controls", find(root, "usersCreateButton").property("visible"), False)
    conn.role = "admin"
    accounts = [{"username": "admin", "role": "admin", "createdAt": "2030-01-01T00:00:00.000Z"}, {"username": "ana", "role": "operator", "createdAt": "2030-01-02T00:00:00.000Z"}, "damaged"]
    user_calls = []

    async def fetch_users():
        user_calls.append(("list",))
        return AccessResult(True, 200, body={"users": list(accounts)})

    async def create_user(username, password, role):
        user_calls.append(("create", username, password, role))
        if username == "ana":
            return AccessResult(False, 400, "rejected", "Username already exists")
        return AccessResult(True, 200, body={"success": True})

    async def update_user(username, new_username="", password="", role=""):
        user_calls.append(("update", username, new_username, password, role))
        return AccessResult(True, 200, body={"success": True})

    async def delete_user(username):
        user_calls.append(("delete", username))
        return AccessResult(False, 400, "rejected", "Cannot delete the last remaining admin account")

    conn.fetch_users = fetch_users
    conn.create_user = create_user
    conn.update_user = update_user
    conn.delete_user = delete_user
    bridge.navigatePanel("robot")
    bridge.navigatePanel("users")
    settle(loop, 6)
    check("users: opening the screen reads the accounts", user_calls[:1], [("list",)])
    check("users: a damaged entry is skipped and the others listed", [row["username"] for row in bridge.usersRows], ["admin", "ana"])
    check("users: the screen has the controls for an administrator", (find(root, "usersCreateButton").property("visible"), find(root, "usersList") is not None), (True, True))
    bridge.createUser("bob", "short", "operator")
    settle(loop, 4)
    check("users: a short password is refused before it is sent", (len(user_calls), "8" in bridge.usersError), (1, True))
    bridge.createUser("bob", "long-enough-1", "nonsense")
    settle(loop, 6)
    check("users: an unknown role becomes operator", user_calls[1], ("create", "bob", "long-enough-1", "operator"))
    check("users: and the list is read again", user_calls[2], ("list",))
    bridge.createUser("ana", "long-enough-1", "operator")
    settle(loop, 6)
    check("users: a name already taken is explained", (bridge.usersMessage, bridge.usersError != ""), ("", True))
    bridge.updateUser("ana", "", "", "")
    check("users: a change with nothing to change is refused", bridge.usersError != "", True)
    bridge.updateUser("ana", "ana2", "", "admin")
    settle(loop, 6)
    check("users: a rename and a new role go out together", [c for c in user_calls if c[0] == "update"], [("update", "ana", "ana2", "", "admin")])
    bridge.deleteUser("admin")
    settle(loop, 6)
    check("users: the last administrator cannot be deleted", bridge.usersError, _("USERS_ERR_LAST_ADMIN"))
    bridge.setAuditLimit(100)
    settle(loop, 4)

    # --- the access options of the Server Admin screen ---
    from hydra_suite.panel_logic import server_security

    options_body = {
        "port": 3000, "pendingPort": None,
        "aiAccess": {"value": "open", "source": "default"},
        "infoAuth": {"value": True, "source": "config"},
        "tls": {"enabled": False, "source": "default", "certPath": "", "keyPath": "", "fingerprint256": None, "active": False, "appliesOnRestart": False},
        "ble": {"mode": {"value": "state", "source": "config"}, "requireEncryption": {"value": True, "source": "default"}, "activeMode": "off", "appliesOnRestart": True},
    }
    conn.role = "admin"
    bridge._security_state = server_security.parse_state(options_body)
    bridge.navigatePanel("robot")
    bridge.navigatePanel("admin_server")
    bridge.changed.emit()
    settle(loop, 4)
    check("security: the card is there for an administrator", (find(root, "securityCard").property("visible"), find(root, "securityBleCombo").property("visible")), (True, True))
    check("security: the view says what the server has", (bridge.securityView["aiValue"], bridge.securityView["infoValue"], bridge.securityView["bleMode"], bridge.securityView["bleEncryption"]), ("open", True, "state", True))
    check("security: and that the running server still has the old Bluetooth mode until it restarts", bridge.securityView["bleRunning"], _("SECURITY_BLE_RUNNING", mode=_("SECURITY_BLE_OFF")) + " " + _("SECURITY_RESTART_NOTE"))
    sent_options = []

    async def put_admin_server_config(patch):
        sent_options.append(patch)
        merged = dict(options_body)
        if "aiAccess" in patch:
            merged["aiAccess"] = {"value": patch["aiAccess"], "source": "config"}
        warnings = ["ble_commands_unencrypted"] if patch.get("ble", {}).get("mode") == "commands" and patch["ble"].get("requireEncryption") is False else []
        return 200, {**merged, "success": True, "warnings": warnings}

    conn.put_admin_server_config = put_admin_server_config
    bridge.setAiAccess("admin")
    settle(loop, 6)
    check("security: choosing who may use the AI relay sends it", sent_options[-1:], [{"aiAccess": "admin"}])
    check("security: and the screen shows the answer", (bridge.securityView["aiValue"], bridge.securityMessage != "", bridge.securityError), ("admin", True, ""))
    bridge.setAiAccess("everyone")
    settle(loop, 3)
    check("security: a value that is not offered sends nothing", len(sent_options), 1)
    check("security: turning the sign-in off asks first, turning it on does not", (bridge.infoAuthNeedsConfirmation(False), bridge.infoAuthNeedsConfirmation(True)), (True, False))
    bridge.saveTlsOptions(True, "", "/k")
    settle(loop, 3)
    check("security: TLS needs both paths and says so without asking the server", (len(sent_options), bridge.securityError != ""), (1, True))
    bridge.saveTlsOptions(True, " /c ", " /k ")
    settle(loop, 6)
    check("security: both paths go out trimmed", sent_options[-1], {"tls": {"enabled": True, "certPath": "/c", "keyPath": "/k"}})
    check("security: commands over Bluetooth without encryption ask first", (bridge.bleNeedsConfirmation("commands", False), bridge.bleNeedsConfirmation("commands", True), bridge.bleNeedsConfirmation("state", False)), (True, False, False))
    bridge.setBleOptions("commands", False)
    settle(loop, 6)
    check("security: the Bluetooth options go out together", sent_options[-1], {"ble": {"mode": "commands", "requireEncryption": False}})
    check("security: and the warning of the server stays on screen", bridge.securityWarning, _("SECURITY_BLE_UNENCRYPTED_WARNING"))
    bridge.setBleOptions("everything", True)
    settle(loop, 3)
    check("security: an unknown Bluetooth mode sends nothing", len(sent_options), 3)
    locked = dict(options_body, aiAccess={"value": "admin", "source": "env"})
    bridge._security_state = server_security.parse_state(locked)
    bridge.changed.emit()
    settle(loop, 3)
    check("security: a value fixed by the environment of the server is locked", (bridge.securityView["aiLocked"], find(root, "securityAiCombo").property("enabled")), (True, False))
    bridge._security_state = server_security.parse_state({k: v for k, v in options_body.items() if k != "ble"})
    bridge.changed.emit()
    settle(loop, 3)
    check("security: a server without the Bluetooth service shows the other options only", (find(root, "securityCard").property("visible"), find(root, "securityBleCombo").property("visible")), (True, False))
    bridge._security_state = server_security.parse_state({"port": 3000})
    bridge.changed.emit()
    settle(loop, 3)
    check("security: a server that predates the options shows no card", find(root, "securityCard").property("visible"), False)
    conn.role = "operator"
    bridge.navigatePanel("robot")

    # --- the setting of conditional writes ---
    bridge.navigatePanel("robot")
    settle(loop)
    combo = find(root, "conditionalModeCombo")
    check("conditional: the selector exists and shows the default", (combo is not None, bridge.conditionalMode), (True, "standard"))
    bridge.setConditionalMode("strict")
    check("conditional: choosing a mode takes effect", (bridge.conditionalMode, access.CONDITIONAL.mode), ("strict", "strict"))
    bridge.setConditionalMode("nonsense")
    check("conditional: an unknown mode changes nothing", access.CONDITIONAL.mode, "strict")
    bridge.setConditionalMode("standard")

    # --- the XY table jog goes out as one atomic table move ---
    sent_commands = []

    async def send_command(robot_id, command, params=None, local_mutate=None, debounce_ms=0):
        sent_commands.append((robot_id, command, params))
        if local_mutate is not None:
            target = conn.state.active_controller.robot_by_id(str(robot_id))
            local_mutate(target)

    conn.send_command = send_command
    bridge.navigatePanel("xy_table")
    settle(loop)
    robot = conn.state.active_controller.robot_by_id("1")
    robot.set_xy_table({"pos": {"x": 10.0, "y": 20.0}, "tableSize": {"width": 300, "length": 300}})
    bridge._xy_robots_cache = conn.state.active_controller.robots
    bridge._xy_selected_robot_id = "1"
    bridge.setXyJogStep(5.0)
    bridge.jogXyTable("x", 1)
    settle(loop, 4)
    check("xy table: a jog is one table command with the position reached", sent_commands, [("1", "table", {"x": 15.0, "y": 20.0, "mode": "absolute"})])
    check("xy table: the local table follows at once", robot.xy_table["pos"]["x"], 15.0)

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
