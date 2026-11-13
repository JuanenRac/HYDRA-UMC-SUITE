# =============================================================================
# HYDRA-UMC SUITE - tests/verify_bridge_signals.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The signals of the Qt Quick bridge, so that a clock tick does not re-evaluate the whole interface:
#   - the properties of the connection lists notify a signal of their own, not the general `changed`
#   - the one-second clock of those lists announces that signal and never `changed`
#   - a general `changed` still reaches the connection lists (nothing that announces a change is left without an effect)
#   - while the clock is not running no signal is emitted
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import asyncio
import sys

sys.path.insert(0, ".")

import qasync
from PySide6.QtGui import QGuiApplication

import qt_suite as qs
from hydra_suite.app import SuiteController

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


app = QGuiApplication.instance() or QGuiApplication(sys.argv)
loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)
bridge = qs.SuiteQtBridge(SuiteController())

meta = bridge.metaObject()
GROUP = ["adminClientsStatusText", "adminClientsShowStats", "adminClientsConnectedCount", "adminClientsAdminCount", "adminClientsRows",
         "connectionHistoryStatus", "connectionClientRows", "connectionEventRows"]


def notify_of(name: str) -> str:
    prop = meta.property(meta.indexOfProperty(name))
    return bytes(prop.notifySignal().name()).decode()


for name in GROUP:
    check(f"{name} notifies the signal of the connection lists", notify_of(name), "_adminClientsChanged")
check("a property of another screen still notifies the general signal", notify_of("securityWarning"), "changed")

general, group = [], []
bridge.changed.connect(lambda: general.append(1))
bridge._adminClientsChanged.connect(lambda: group.append(1))

job = bridge._admin_clients_tick_timer
job._callback()
check("the clock announces the connection lists", len(group), 1)
check("the clock does not announce the general change", len(general), 0)

bridge.changed.emit()
check("a general change reaches the connection lists", (len(general), len(group)), (1, 2))

general.clear()
group.clear()
check("the clock job is the one-second job of the admin screen", (job.name, job.interval()), ("admin_clients_clock", 1000))
check("nothing was emitted by looking at the job", (len(general), len(group)), (0, 0))

print("BRIDGE_SIGNALS=PASS" if failures == 0 else f"BRIDGE_SIGNALS=FAIL ({failures})")
sys.exit(1 if failures else 0)
