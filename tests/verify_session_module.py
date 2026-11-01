# =============================================================================
# HYDRA-UMC SUITE - tests/verify_session_module.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The session of a server in one object (net/session.py): who is signed in, the refresh, the role, the rule that an
# operator or a viewer does not change the global settings, and how HydraConnection reads and writes it. Headless; no
# network: the answers of the server are plain dicts.
# =============================================================================
import asyncio
import sys

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

import qt_suite as qs
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.client import HydraConnection
from hydra_suite.net.session import Session

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def pure() -> None:
    s = Session()
    check("session: nothing is known at first", (s.token, s.role, s.login_ok, s.is_admin, s.auth_headers()), (None, None, None, False, {}))
    check("session: an answer without a token changes nothing", (s.accept_login({"role": "admin"}), s.token, s.login_ok), (False, None, None))
    check("session: nonsense is not an answer", (s.accept_login(None), s.accept_login("token"), s.accept_login({"token": 5})), (False, False, False))
    s.login_rejected = True
    s.login_retry_after_s = 30.0
    s.needs_totp = True
    check("session: a login stores the token, the refresh token and the role and clears the refusal", (s.accept_login({"token": "t1", "refreshToken": "r1", "role": "operator"}), s.token, s.refresh_token, s.role, s.login_ok, s.login_rejected, s.login_retry_after_s, s.needs_totp), (True, "t1", "r1", "operator", True, False, None, False))
    check("session: the header carries the token", s.auth_headers(), {"Authorization": "Bearer t1"})
    check("session: an operator does not change the global settings, an administrator does, an unknown role is left to the server", (s.may_edit_settings, Session(role="viewer").may_edit_settings, Session(role="admin").may_edit_settings, Session().may_edit_settings), (False, False, True, True))
    check("session: a refresh keeps the role it did not repeat and rotates the refresh token", (s.accept_refresh({"token": "t2", "refreshToken": "r2"}), s.token, s.refresh_token, s.role), (True, "t2", "r2", "operator"))
    check("session: a refresh answer without a token is refused and changes nothing", (s.accept_refresh({"refreshToken": "x"}), s.token, s.refresh_token), (False, "t2", "r2"))
    check("session: a refresh may change the role", (s.accept_refresh({"token": "t3", "role": "admin"}), s.role, s.is_admin), (True, "admin", True))
    s.drop_access_token()
    check("session: dropping the access token keeps the refresh token", (s.token, s.refresh_token), (None, "r2"))
    s.drop()
    check("session: dropping the session forgets both", (s.token, s.refresh_token), (None, None))
    s.reject_login(needs_totp=True)
    check("session: a refusal of the credentials stops the retries and may ask for the code", (s.login_rejected, s.needs_totp, s.login_ok), (True, True, False))
    s.fail_login(12.5)
    check("session: a limiter wait is kept", (s.login_ok, s.login_retry_after_s), (False, 12.5))
    s.totp_code = "123456"
    check("session: the code of the second step is taken once", (s.take_totp_code(), s.take_totp_code()), ("123456", ""))


def through_the_connection() -> None:
    conn = HydraConnection(ServerInfo(host="10.0.0.9", port=3000, username="ana", password="pw"))
    conn._token = "tok"
    conn.role = "operator"
    conn.login_ok = True
    check("connection: the old fields read the session", (conn.session.token, conn.session.role, conn.session.login_ok), ("tok", "operator", True))
    conn.session.accept_login({"token": "other", "role": "admin"})
    check("connection: and follow it", (conn._token, conn.role, conn.is_admin, conn.may_edit_settings, conn.auth_headers()), ("other", "admin", True, True, {"Authorization": "Bearer other"}))
    conn.role = "viewer"
    check("connection: a viewer may not edit the global settings", conn.may_edit_settings, False)


def bridge_lock() -> None:
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    for timers in bridge._poller_gates().values():
        for timer in timers:
            timer.stop()
    check("bridge: without a server nothing is locked", (bridge.canEditSettings, bridge.settingsLocked), (True, False))
    conn = HydraConnection(ServerInfo(host="10.0.0.9", port=3000, username="ana", password="pw"))
    conn.login_ok = True
    conn.role = "operator"
    conn.state = HydraState({"activeControllerId": "c1", "settings": {}, "controllers": [{"id": "c1", "robots": []}]})
    controller.connections["10.0.0.9:3000"] = conn
    controller._active_id = "10.0.0.9:3000"
    check("bridge: an operator may not edit the global settings", bridge.canEditSettings, False)
    check("bridge: but the screens that only read are not locked", bridge.settingsLocked, False)
    for panel in ("xy_table", "rack", "pick_and_place", "cameras", "robots_catalog", "atc"):
        bridge._active_key = panel
        check(f"bridge: {panel} is locked for an operator", bridge.settingsLocked, True)
    bridge._active_key = "robot"
    check("bridge: the robot control (commands, not settings) is never locked", bridge.settingsLocked, False)
    conn.role = "admin"
    bridge._active_key = "xy_table"
    check("bridge: an administrator edits everything", (bridge.canEditSettings, bridge.settingsLocked), (True, False))


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    pure()
    through_the_connection()
    bridge_lock()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
