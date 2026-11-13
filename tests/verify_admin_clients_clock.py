# =============================================================================
# HYDRA-UMC SUITE - tests/verify_admin_clients_clock.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The one-second clock of the Admin Clients screen reaches only the rows that show how long each client has been connected,
# not every property of the bridge (it used to emit the one `changed` signal that some three hundred properties listen to):
#   - a tick of the clock emits `_adminClientsChanged` and does not emit `changed`
#   - `adminClientsRows` is notified by `_adminClientsChanged`
#   - new data from the server emits both, so the counts and the status text still follow
# Run headless: QT_QPA_PLATFORM=offscreen. No network: the connection is a fake.
# =============================================================================
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import qasync
from PySide6.QtGui import QGuiApplication

from hydra_suite import i18n
from hydra_suite.app import SuiteController

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


class FakeAdminConnection:
    is_admin = True

    async def fetch_admin_clients(self):
        return 200, {"clients": [{"username": "ana", "role": "admin", "remoteAddress": "10.0.0.5", "connected": True, "connectedAt": None}]}


def main() -> None:
    import qt_suite as qs

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    controller = SuiteController()
    bridge = qs.SuiteQtBridge(controller)
    for timer in (bridge._admin_clients_timer, bridge._admin_logs_timer, bridge._camera_status_timer):
        timer.stop()

    counts = {"changed": 0, "clients": 0}
    bridge.changed.connect(lambda: counts.__setitem__("changed", counts["changed"] + 1))
    bridge._adminClientsChanged.connect(lambda: counts.__setitem__("clients", counts["clients"] + 1))

    meta = bridge.metaObject()
    def text(value) -> str:
        return value.decode() if isinstance(value, (bytes, bytearray)) else str(value)

    notify = {text(meta.property(i).name()): text(bytes(meta.property(i).notifySignal().name())) for i in range(meta.propertyCount()) if meta.property(i).hasNotifySignal()}
    check("the rows are notified by their own signal", notify.get("adminClientsRows"), "_adminClientsChanged")
    check("the counts still follow the general signal", notify.get("adminClientsConnectedCount"), "changed")

    bridge._admin_clients_tick_timer._callback()
    check("a tick of the clock reaches the rows only", (counts["changed"], counts["clients"]), (0, 1))
    bridge._admin_clients_tick_timer._callback()
    check("and so does every later tick", (counts["changed"], counts["clients"]), (0, 2))

    counts.update(changed=0, clients=0)
    fake = FakeAdminConnection()
    type(controller).active_connection = property(lambda self: fake)  # type: ignore[assignment,misc]
    loop.run_until_complete(bridge._refresh_admin_clients_list())
    check("new data from the server emits both signals", (counts["changed"] >= 1, counts["clients"] >= 1), (True, True))
    check("and the rows and the counts show it", (len(bridge.adminClientsRows), bridge.adminClientsConnectedCount, bridge.adminClientsAdminCount), (1, 1, 1))
    loop.close()


if __name__ == "__main__":
    folder = tempfile.mkdtemp(prefix="suite_admin_clock_")
    i18n.CONFIG_FILE_PATH = Path(folder) / "hydra_suite_config.json"  # the real configuration file is never touched
    main()
    if failures:
        print(f"verify_admin_clients_clock: {failures} FAILED")
        sys.exit(1)
    print("verify_admin_clients_clock: OK")
