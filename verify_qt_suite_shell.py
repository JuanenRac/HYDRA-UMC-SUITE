# =============================================================================
# HYDRA-UMC SUITE - real, hardware/network-free check of the Qt Quick shell
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Deliberately kept outside tests/ - same real reason as URTC-TESTER/
URTC-FLASHER's own verify_qt_*.py scripts: exercises a real Qt event loop
and real QML load. Run directly:
    QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py
"""
from __future__ import annotations

import asyncio
import logging
import sys

import qasync
from PySide6.QtGui import QGuiApplication

from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState
from hydra_suite.ui.nav_sidebar import ALL_DOCK_KEYS
from qt_suite import MIGRATED_PANELS, SuiteQtBridge


def _run() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    # Real qasync loop - SuiteController.add_server()/remove_server()
    # (app.py) schedule real asyncio.ensure_future() work, same real
    # requirement qt_suite.py's own run_qtquick() sets up before
    # anything touches SuiteController.
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    controller = SuiteController()
    bridge = SuiteQtBridge(controller)

    # --- nav taxonomy real parity with nav_sidebar.py's own real dock keys ---
    all_keys = set()
    for items in (bridge.rootItems, bridge.industrialItems, bridge.urtcItems, bridge.hydraumcItems, bridge.hydraumcEcosystemItems):
        all_keys.update(item["key"] for item in items)
    assert all_keys == set(ALL_DOCK_KEYS), (
        f"QML nav taxonomy must match nav_sidebar.py's own ALL_DOCK_KEYS exactly - "
        f"missing={ALL_DOCK_KEYS - all_keys} extra={all_keys - ALL_DOCK_KEYS}"
    )
    assert MIGRATED_PANELS <= all_keys, "every migrated panel key must be a real nav key"

    # --- navigation ---
    assert bridge.activePanel == "overview"
    assert bridge.activePanelMigrated is True
    bridge.navigatePanel("cnc")
    assert bridge.activePanel == "cnc"
    assert bridge.activePanelMigrated is False, "cnc is not in MIGRATED_PANELS yet"
    bridge.navigatePanel("logs")
    assert bridge.activePanelMigrated is True

    # --- logs: real logging.Logger records reach the bridge, real filters apply ---
    log = logging.getLogger("verify_qt_suite_shell")
    log.info("hello from a real logger")
    assert any("hello from a real logger" in e["message"] for e in bridge.logEntries)
    before = len(bridge.logEntries)
    log.debug("a debug line")
    bridge.setLogLevelFilter("INFO")
    assert not any(e["level"] == "DEBUG" for e in bridge.logEntries), "level filter must actually filter"
    bridge.setLogLevelFilter(bridge.uiText("LOG_LEVEL_ALL"))
    log.warning("distinctive-search-needle-xyz")
    bridge.setLogSearchFilter("distinctive-search-needle-xyz")
    assert len(bridge.logEntries) == 1 and "distinctive-search-needle-xyz" in bridge.logEntries[0]["message"]
    bridge.setLogSearchFilter("")
    bridge.clearLogs()
    assert bridge.logEntries == []

    # --- servers: real ServerInfo/HydraConnection objects, no network ---
    assert bridge.serverRows == []
    bridge.addManualServer("", 3000, "u", "p")  # empty host must be rejected
    assert bridge.serverRows == []
    bridge.addManualServer("10.0.0.9", 3000, "", "p")  # missing username must be rejected
    assert bridge.serverRows == []
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    assert len(bridge.serverRows) == 1
    conn_id = bridge.serverRows[0]["connId"]
    assert bridge.serverRows[0]["hostPort"] == "10.0.0.9:3000"
    assert bridge.serverRows[0]["active"] is True, "the first server added becomes active automatically"
    creds = bridge.serverCredentials(conn_id)
    assert creds["username"] == "admin" and creds["password"] == "hunter2"
    bridge.saveServerCredentials(conn_id, "admin2", "newpass")
    assert bridge.serverCredentials(conn_id)["username"] == "admin2"
    bridge.removeServer(conn_id)
    assert bridge.serverRows == []

    # --- overview: real controller signals reach the bridge ---
    fake_state = HydraState({
        "settings": {},
        "activeControllerId": "c1",
        "controllers": [
            {
                "id": "c1", "name": "Test Cell", "ip": "10.0.0.5",
                "robots": [
                    {"id": "r1", "model": "6DOF", "role": "Idle", "online": True, "speed": 80, "acceleration": 50},
                    {"id": "r2", "model": "6DOF", "role": "Idle", "online": False, "speed": 100, "acceleration": 100},
                ],
            }
        ],
    })
    controller.active_state_changed.emit(fake_state)
    assert bridge.overviewName == "Test Cell"
    assert bridge.overviewIp == "10.0.0.5"
    assert bridge.overviewRobotCount == "2"
    assert bridge.overviewOnlineCount == "1 / 2"
    assert len(bridge.overviewRobots) == 2
    assert bridge.overviewRobots[0]["online"] is True

    controller.active_metrics_changed.emit({"cpu_load": 42, "memory_usage": 55, "temp": 61.4, "uptime": 3725})
    assert bridge.overviewCpu == "42%"
    assert bridge.overviewTemp == "61°C"
    assert bridge.overviewUptime == "1h 2m"

    # --- QML itself loads with zero warnings ---
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    qml_controller = SuiteController()
    qml_bridge = SuiteQtBridge(qml_controller)
    engine.rootContext().setContextProperty("suiteBackend", qml_bridge)
    engine.rootContext().setContextProperty("controller", qml_controller)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(str(w) for w in ws))
    engine.load("assets/qml/Main.qml")
    assert engine.rootObjects(), "Main.qml must load with the real bridge"
    assert not warnings, f"QML must load with zero warnings, got: {warnings}"

    print("verify_qt_suite_shell: all real assertions passed")


if __name__ == "__main__":
    _run()
