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

# --- the reservations of the Robot Control screen, the health of the ecosystem and the Flasher ---------------------------------
from hydra_suite.models import HydraState

check("a reservation property notifies the signal of the access clock", notify_of("selectedRobotMode"), "_accessChanged")
check("a health property notifies the signal of the health clock", notify_of("ecoHealthStatus"), "_ecoHealthChanged")
check("a Flasher property notifies the signal of the Flasher", notify_of("flasherTier"), "flasherChanged")


def count(signal_names):
    seen = {}
    for name in signal_names:
        seen[name] = []
        getattr(bridge, name).connect(lambda n=name: seen[n].append(1))
    return seen


seen = count(["changed", "_accessChanged", "_ecoHealthChanged", "flasherChanged"])
bridge._access_tick_timer._callback()
check("the access clock announces its own signal only", (len(seen["changed"]), len(seen["_accessChanged"]), len(seen["flasherChanged"])), (0, 1, 0))
bridge._eco_health_tick._callback()
check("the health clock announces its own signal only", (len(seen["changed"]), len(seen["_ecoHealthChanged"]), len(seen["flasherChanged"])), (0, 1, 0))
bridge._on_flasher_state_changed(HydraState({}))
check("a state change of the server reaches the Flasher without a general change", (len(seen["changed"]), len(seen["flasherChanged"])), (0, 1))
bridge.changed.emit()
check("a general change reaches all of them", (len(seen["_accessChanged"]), len(seen["_ecoHealthChanged"]), len(seen["flasherChanged"])), (2, 2, 2))

# --- the Rack Manager, Pick and Place and XY Table screens -------------------------------------------------------------------
for prop, signal in (("rackRobotOptions", "rackChanged"), ("pnpRobotOptions", "pnpChanged"), ("xyRobotOptions", "xyTableChanged")):
    check(f"{prop} notifies {signal}", notify_of(prop), signal)

screens = count(["changed", "rackChanged", "pnpChanged", "xyTableChanged"])
state = HydraState({})
bridge._on_rack_state_changed(state)
check("a state change reaches the Rack Manager only", (len(screens["changed"]), len(screens["rackChanged"]), len(screens["pnpChanged"]), len(screens["xyTableChanged"])), (0, 1, 0, 0))
bridge._on_pnp_state_changed(state)
check("a state change reaches Pick and Place only", (len(screens["changed"]), len(screens["rackChanged"]), len(screens["pnpChanged"]), len(screens["xyTableChanged"])), (0, 1, 1, 0))
bridge._on_xy_state_changed(state)
check("a state change reaches the XY Table only", (len(screens["changed"]), len(screens["rackChanged"]), len(screens["pnpChanged"]), len(screens["xyTableChanged"])), (0, 1, 1, 1))
bridge.changed.emit()
check("a general change reaches the three screens", (len(screens["rackChanged"]), len(screens["pnpChanged"]), len(screens["xyTableChanged"])), (2, 2, 2))

# --- the Module Config, ATC Tools and Tester screens -----------------------------------------------------------------------------
for prop, signal in (("moduleSelectedRobotId", "moduleChanged"), ("atcSelectedRobotId", "atcChanged"), ("testerSelectedRobotId", "testerChanged")):
    check(f"{prop} notifies {signal}", notify_of(prop), signal)

tools = count(["changed", "moduleChanged", "atcChanged", "testerChanged", "flasherChanged"])
bridge._on_module_state_changed(state)
bridge._on_atc_state_changed(state)
check("a state change reaches the Module Config and ATC Tools screens only", (len(tools["changed"]), len(tools["moduleChanged"]), len(tools["atcChanged"]), len(tools["testerChanged"])), (0, 1, 1, 0))
bridge._on_tester_state_changed(state)
check("a state change of the Tester reaches the Tester and the Flasher, which shows the same CAN link flag", (len(tools["changed"]), len(tools["testerChanged"]), len(tools["flasherChanged"])), (0, 1, 1))
bridge.changed.emit()
check("a general change reaches the three screens", (len(tools["moduleChanged"]), len(tools["atcChanged"]), len(tools["testerChanged"])), (2, 2, 2))

# --- the Kinematic Brain Stage and Overview screens -----------------------------------------------------------------------------
for prop, signal in (("kbsHasController", "kbsChanged"), ("overviewName", "overviewChanged")):
    check(f"{prop} notifies {signal}", notify_of(prop), signal)

more = count(["changed", "kbsChanged", "overviewChanged"])
bridge._on_kbs_state_changed(state)
check("a state change reaches the Kinematic Brain Stage only", (len(more["changed"]), len(more["kbsChanged"]), len(more["overviewChanged"])), (0, 1, 0))
bridge._on_overview_state_changed(state)
bridge._on_overview_metrics_changed({"cpu_load": 12, "memory_usage": 40, "temp": 51, "uptime": 3700})
check("the state and the metrics of the Overview reach the Overview only", (len(more["changed"]), len(more["kbsChanged"]), len(more["overviewChanged"])), (0, 1, 2))
check("the metrics are shown", (bridge.overviewCpu, bridge.overviewUptime), ("12%", "1h 1m"))
bridge.changed.emit()
check("a general change reaches both", (len(more["kbsChanged"]), len(more["overviewChanged"])), (2, 3))

# --- settings and security ----------------------------------------------------------------------------------------------------
for prop in ("safetyIsAdmin", "usersIsAdmin", "adminServerStatusText"):
    if meta.indexOfProperty(prop) >= 0:
        check(f"{prop} notifies securityChanged", notify_of(prop), "securityChanged")

security = count(["changed", "securityChanged"])
bridge.setAuditType("all")
check("choosing the kind of the audit record announces the security group only", (len(security["changed"]), len(security["securityChanged"])), (0, 1))
bridge.changed.emit()
check("a general change reaches the security group", len(security["securityChanged"]), 2)

print("BRIDGE_SIGNALS=PASS" if failures == 0 else f"BRIDGE_SIGNALS=FAIL ({failures})")
sys.exit(1 if failures else 0)
