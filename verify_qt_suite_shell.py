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
import os
import sys
import tempfile

import qasync
from PySide6.QtGui import QGuiApplication

from hydra_suite.app import SuiteController
from hydra_suite.models import RACK_MAX_CAPACITY, HydraState
from hydra_suite.ui.nav_sidebar import ALL_DOCK_KEYS
from hydra_suite.ui.panels.admin_server_panel import _format_uptime
from hydra_suite.can_ota import GithubFirmwareAsset, VersionQueryResult
from hydra_suite.ui.panels.atc_tools_panel import URTC_TOOLS
import qt_suite as qs
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
    # Real background poll timers (admin clients/logs) start ticking the
    # moment the bridge is constructed - stopped for the rest of this
    # deterministic script so a stray real tick can never race an
    # explicit loop.run_until_complete() call below.
    bridge._admin_clients_timer.stop()
    bridge._admin_logs_timer.stop()
    bridge._camera_status_timer.stop()

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
    bridge.navigatePanel("viewport")
    assert bridge.activePanel == "viewport"
    assert bridge.activePanelMigrated is False, "viewport is not in MIGRATED_PANELS yet"
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

    # --- ai family: real HydraConnection.fetch_ecosystem_status() shape,
    # network call itself stubbed (this bridge's own real responsibility
    # is grouping/labeling the response, not the HTTP call) ---
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    ai_conn_id = bridge.serverRows[0]["connId"]
    ai_conn = controller.connections[ai_conn_id]

    async def _fake_ecosystem_status():
        return (200, {
            "available": True,
            "projects": [
                {"family": "Vision AI Node", "name": "vision-node-1", "role": "inference", "version": "1.2.0", "live": True},
                {"family": "Cognitive AI Node", "name": "cognitive-node-1", "role": "planner", "version": "0.9.0", "live": False},
                {"family": "Datalake", "name": "datalake-1", "role": "storage", "version": "2.0.0", "live": True},  # not an AI family - must be filtered out
            ],
        })

    ai_conn.fetch_ecosystem_status = _fake_ecosystem_status
    ai_conn.state.raw["settings"] = {"aiHailo": {"visionDevice": "none", "cognitiveDevice": "hailo10"}}
    loop.run_until_complete(bridge._refresh_ai_family())
    groups = {g["title"]: g for g in bridge.aiFamilyGroups}
    assert len(bridge.aiFamilyGroups) == 2, "only the 2 real AI families, Datalake must be filtered out"
    vision = next(g for g in bridge.aiFamilyGroups if len(g["projects"]) == 1 and g["projects"][0]["name"] == "vision-node-1")
    assert vision["deviceConfigured"] is False, "visionDevice is 'none' in the fake settings"
    assert vision["mismatchWarning"] != "", "a live Vision project with no configured device must warn"
    cognitive = next(g for g in bridge.aiFamilyGroups if g["projects"] and g["projects"][0]["name"] == "cognitive-node-1")
    assert cognitive["deviceConfigured"] is True
    assert cognitive["mismatchWarning"] == "", "no warning when the family has a real device configured"
    assert cognitive["projects"][0]["live"] is False
    bridge.removeServer(ai_conn_id)

    # --- admin clients: real admin gate + sort + relative duration ---
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    ac_conn_id = bridge.serverRows[0]["connId"]
    ac_conn = controller.connections[ac_conn_id]
    ac_conn.role = None  # not an admin session yet
    loop.run_until_complete(bridge._refresh_admin_clients())
    assert bridge.adminClientsRows == [], "a non-admin session must never show any real client list"
    assert bridge.adminClientsStatusText == bridge.uiText("MSG_ADMIN_ONLY")

    ac_conn.role = "admin"

    async def _fake_admin_clients():
        return (200, {"clients": [
            {"username": "bob", "role": "operator", "remoteAddress": "10.0.0.20", "connected": True, "connectedAt": None},
            {"username": "alice", "role": "admin", "remoteAddress": "10.0.0.21", "connected": True, "connectedAt": None},
        ]})

    ac_conn.fetch_admin_clients = _fake_admin_clients
    loop.run_until_complete(bridge._refresh_admin_clients())
    assert bridge.adminClientsConnectedCount == 2
    assert bridge.adminClientsAdminCount == 1
    assert bridge.adminClientsShowStats is True
    rows = bridge.adminClientsRows
    assert rows[0]["username"] == "alice" and rows[0]["isAdmin"] is True, "admin-first sort, same as the classic panel"
    assert rows[1]["username"] == "bob" and rows[1]["isAdmin"] is False
    bridge.removeServer(ac_conn_id)

    # --- admin logs: real tag extraction, filtering, and the real
    # "clear the screen, keep tailing" anchor trick ---
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    al_conn_id = bridge.serverRows[0]["connId"]
    al_conn = controller.connections[al_conn_id]
    al_conn.role = "admin"
    fake_lines = ["[ADMIN] first line", "[WS] second line", "[ADMIN] third line"]

    async def _fake_admin_logs(_lines):
        # A real GET /api/admin/logs response is fresh JSON every call,
        # never the same list object twice - returning a copy here
        # (rather than the closed-over fake_lines directly) avoids
        # accidentally aliasing this test's own fixture with
        # self._admin_logs_all_lines, which a real HTTP response could
        # never do.
        return (200, {"lines": list(fake_lines)})

    al_conn.fetch_admin_logs = _fake_admin_logs
    loop.run_until_complete(bridge._refresh_admin_logs())
    assert bridge.adminLogsLines == fake_lines
    assert set(bridge.adminLogsTags) == {"ADMIN", "WS"}
    bridge.setAdminLogsTagFilter("ADMIN")
    assert bridge.adminLogsLines == ["[ADMIN] first line", "[ADMIN] third line"]
    bridge.setAdminLogsTagFilter("")
    bridge.setAdminLogsSearch("third")
    assert bridge.adminLogsLines == ["[ADMIN] third line"]
    bridge.setAdminLogsSearch("")

    # Clear anchors on the last line currently held - a later poll that
    # only appends past it must show just the new lines, matching
    # admin_logs_panel.py's own real "keep tailing" behavior.
    bridge.clearAdminLogs()
    assert bridge.adminLogsLines == [bridge.uiText("MSG_LOGS_NONE")]
    fake_lines = fake_lines + ["[ADMIN] fourth line"]
    loop.run_until_complete(bridge._refresh_admin_logs())
    assert bridge.adminLogsLines == ["[ADMIN] fourth line"]

    # Pausing must skip the next real poll entirely.
    bridge.toggleAdminLogsLive()
    assert bridge.adminLogsLive is False
    fake_lines.append("[ADMIN] should not appear while paused")
    loop.run_until_complete(bridge._refresh_admin_logs())
    assert bridge.adminLogsLines == ["[ADMIN] fourth line"], "a paused panel must not pick up a new poll"
    bridge.toggleAdminLogsLive()
    bridge.removeServer(al_conn_id)

    # --- admin server: real port config load/save + hydra-info snapshot ---
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    as_conn_id = bridge.serverRows[0]["connId"]
    as_conn = controller.connections[as_conn_id]
    as_conn.role = "admin"

    async def _fake_server_config():
        return (200, {"port": 3000, "pendingPort": None})

    async def _fake_hydra_info():
        return (200, {"product": "HYDRA-UMC Server", "appVersion": "1.4.0", "uptimeSeconds": 7384, "controllerCount": 2, "robotCount": 5, "hostname": "hydra-cell-1"})

    as_conn.fetch_admin_server_config = _fake_server_config
    as_conn.fetch_hydra_info = _fake_hydra_info
    loop.run_until_complete(bridge._refresh_admin_server())
    assert bridge.adminServerInfoVisible is True
    assert bridge.adminServerProduct == "HYDRA-UMC Server"
    assert bridge.adminServerVersion == "v1.4.0"
    assert bridge.adminServerUptime == _format_uptime(7384)
    assert bridge.adminServerControllerCount == "2" and bridge.adminServerRobotCount == "5"
    assert bridge.adminServerHost == "hydra-cell-1"
    assert bridge.adminServerPendingPortText == "3000"

    save_calls = []

    async def _fake_save_port(port):
        save_calls.append(port)
        return (200, {})

    as_conn.save_admin_server_port = _fake_save_port
    loop.run_until_complete(bridge._save_admin_server_port("not-a-port"))
    assert save_calls == [], "an invalid port must never reach the real save call"
    assert bridge.adminServerStatusText == bridge.uiText("MSG_ADMIN_SERVER_PORT_INVALID")
    loop.run_until_complete(bridge._save_admin_server_port("70000"))
    assert save_calls == [], "an out-of-range port must never reach the real save call"
    loop.run_until_complete(bridge._save_admin_server_port("8080"))
    assert save_calls == [8080]
    assert bridge.adminServerStatusText == bridge.uiText("MSG_ADMIN_SERVER_PORT_SAVED")

    restart_calls = []

    async def _fake_restart():
        restart_calls.append(True)
        return (200, {})

    as_conn.restart_server = _fake_restart
    loop.run_until_complete(bridge._restart_admin_server())
    assert restart_calls == [True]
    assert bridge.adminServerStatusText == bridge.uiText("MSG_ADMIN_SERVER_RESTART_REQUESTED")
    bridge.removeServer(as_conn_id)

    # --- ecosystem services: real grouping/filtering/stats, and the
    # real start/stop/restart routing (control_service is stubbed - the
    # HTTP call itself isn't this bridge's own surface) ---
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    es_conn_id = bridge.serverRows[0]["connId"]
    es_conn = controller.connections[es_conn_id]
    es_conn.role = "admin"

    async def _fake_es_status():
        return (200, {"available": True, "scannedAt": "12:00:00", "projects": [
            {"name": "vision-node", "family": "AI", "stack": "python", "live": True, "systemdUnit": "vision.service"},
            {"name": "cognitive-node", "family": "AI", "stack": "python", "live": False, "systemdUnit": "cognitive.service"},
            {"name": "server", "family": "Core", "stack": "node", "activeState": "active", "live": True, "serviceHost": "127.0.0.1", "servicePort": 3000, "pid": 4242, "systemdUnit": "server.service"},
        ]})

    es_conn.fetch_ecosystem_status = _fake_es_status
    loop.run_until_complete(bridge._refresh_ecosystem_services())
    assert bridge.esShowStats is True
    assert bridge.esStats["total"] == 3 and bridge.esStats["live"] == 2 and bridge.esStats["families"] == 2
    assert set(bridge.esFamilies) == {"AI", "Core"}
    groups = {g["family"]: g for g in bridge.esGroups}
    assert groups["AI"]["count"] == 2 and groups["Core"]["count"] == 1
    core_card = groups["Core"]["cards"][0]
    assert core_card["hostPort"] == "127.0.0.1:3000"
    assert "4242" in core_card["pidText"]
    assert core_card["canControl"] is True, "an admin session with a real systemdUnit must be controllable"

    bridge.setEsFamilyFilter("AI")
    assert len(bridge.esGroups) == 1 and bridge.esGroups[0]["family"] == "AI"
    bridge.setEsSearch("cognitive")
    assert len(bridge.esGroups[0]["cards"]) == 1 and bridge.esGroups[0]["cards"][0]["name"] == "cognitive-node"
    bridge.setEsSearch("")
    bridge.setEsFamilyFilter("")

    control_calls = []

    async def _fake_control_service(unit, action):
        control_calls.append((unit, action))
        return (200, {})

    es_conn.control_service = _fake_control_service
    loop.run_until_complete(bridge._run_es_service_action("vision.service", "restart"))
    assert control_calls == [("vision.service", "restart")]
    assert bridge._es_actioning_unit is None, "actioning flag must clear once the action resolves"

    async def _fake_control_service_fails(unit, action):
        return (500, {"error": "systemd refused"})

    es_conn.control_service = _fake_control_service_fails
    loop.run_until_complete(bridge._run_es_service_action("vision.service", "stop"))
    vision_card = next(c for g in bridge.esGroups for c in g["cards"] if c["unit"] == "vision.service")
    assert vision_card["errorText"] == "systemd refused"
    bridge.removeServer(es_conn_id)

    # --- ecosystem telemetry: real query/aggregate routing, chart-point
    # normalization math, and stats - fetch_telemetry_query/_aggregate
    # are stubbed (the HTTP call itself isn't this bridge's own
    # surface), the normalization/validation logic is. ---
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    tel_conn_id = bridge.serverRows[0]["connId"]
    tel_conn = controller.connections[tel_conn_id]

    async def _fake_telemetry_query(params):
        return (200, [
            {"timestamp": 1000, "value": 10},
            {"timestamp": 2000, "value": 30},
            {"timestamp": 3000, "value": 20},
        ])

    tel_conn.fetch_telemetry_query = _fake_telemetry_query
    loop.run_until_complete(bridge._run_telemetry_query("query", "robot-1", "temp", "value", "1000", "3000", "60000", "avg"))
    assert bridge.telemetryChartMode == "line"
    pts = bridge.telemetryLinePoints
    assert len(pts) == 3
    assert pts[0]["nx"] == 0.0 and pts[-1]["nx"] == 1.0, "x must normalize across the real timestamp span"
    assert pts[0]["ny"] == 0.0 and pts[1]["ny"] == 1.0, "y must normalize across the real value span (10->0, 30->1)"
    assert bridge.telemetryStats["min"] == "10.00" and bridge.telemetryStats["max"] == "30.00"
    assert bridge.telemetryStats["count"] == "3"

    # Aggregate mode with missing required fields must be rejected
    # client-side, never reaching the real network call.
    aggregate_calls = []

    async def _fake_telemetry_aggregate(params):
        aggregate_calls.append(params)
        return (200, [{"bucketStart": 0, "value": 5}, {"bucketStart": 60000, "value": 15}])

    tel_conn.fetch_telemetry_aggregate = _fake_telemetry_aggregate
    loop.run_until_complete(bridge._run_telemetry_query("aggregate", "", "", "", "", "", "60000", "avg"))
    assert aggregate_calls == [], "aggregate mode must refuse to run with kind/field/start/end all empty"
    assert bridge.telemetryStatusText == bridge.uiText("MSG_TELEMETRY_AGGREGATE_MISSING_FIELDS")

    loop.run_until_complete(bridge._run_telemetry_query("aggregate", "", "temp", "value", "0", "120000", "60000", "avg"))
    assert len(aggregate_calls) == 1
    assert bridge.telemetryChartMode == "bar"
    bars = bridge.telemetryBars
    assert len(bars) == 2
    assert abs(bars[0]["nh"] - (5 / 15)) < 1e-9
    assert bars[1]["nh"] == 1.0

    # A real 503 "not configured" response must clear the chart/stats,
    # not silently keep showing the previous run's data.
    async def _fake_telemetry_unavailable(params):
        return (503, {"available": False})

    tel_conn.fetch_telemetry_query = _fake_telemetry_unavailable
    loop.run_until_complete(bridge._run_telemetry_query("query", "", "", "", "", "", "60000", "avg"))
    assert bridge.telemetryStatusText == bridge.uiText("MSG_TELEMETRY_NOT_CONFIGURED")
    assert bridge.telemetryChartMode == "empty"
    assert bridge.telemetryShowStats is False
    bridge.removeServer(tel_conn_id)

    # --- xy table: real has_xy_table/xy_table quirk (two genuinely
    # separate fields, no-op guards until Reset creates one), own real
    # independent robot selection (not shared with Robot Control) ---
    fake_state_xy = HydraState({
        "settings": {}, "activeControllerId": "c1",
        "controllers": [{"id": "c1", "name": "Cell", "ip": "10.0.0.1", "robots": [
            {"id": "x1", "model": "XY-Bot"},
        ]}],
    })
    controller.active_state_changed.emit(fake_state_xy)
    assert bridge.xySelectedRobotId == "x1"
    assert bridge.xyHasRobot is True
    assert bridge.xyHasTable is False, "a robot with no hasXYTable flag must show the empty state"
    assert bridge.xyCanReset is False, "Reset must stay disabled until a table exists at all"
    assert bridge.xyWidth == 500 and bridge.xyLength == 500, "display fallback is 500mm before any real xyTable object exists"

    push_calls_xy = []
    controller.push_active_state = lambda: push_calls_xy.append(True)
    bridge.enableXyTable()
    # handleAddTable()'s own real quirk: only the flag is set, no
    # xyTable block yet - the classic UI still switches to the settings
    # page on has_xy_table alone (xyHasTable mirrors that flag exactly)
    # and shows the 500mm DISPLAY fallback, but the underlying object is
    # still genuinely None.
    assert bridge.xyHasTable is True
    xy_robot = bridge._xy_selected_robot()
    assert xy_robot.has_xy_table is True
    assert xy_robot.xy_table is None
    assert bridge.xyWidth == 500 and bridge.xyLength == 500

    # The no-op guards: width/jog must do nothing against a robot with
    # the flag but no real xyTable object yet - matches
    # handleSizeChange()/handleJog()'s own real no-op guards.
    before_push_count = len(push_calls_xy)
    bridge.setXyWidth(800)
    bridge.jogXyTable("x", 1)
    assert len(push_calls_xy) == before_push_count, "a no-op guard must never call push_active_state()"
    assert xy_robot.xy_table is None, "still no real table object until Reset"

    bridge.resetXyTable()
    assert bridge.xyHasTable is True
    assert bridge.xyWidth == 300 and bridge.xyLength == 300, "Reset writes 300mm, a real different number from the 500mm display fallback"
    assert bridge.xyPosX == "0.00" and bridge.xyPosY == "0.00"

    bridge.setXyWidth(1200)
    assert bridge.xyWidth == 1200

    bridge.setXyJogStep(10.0)
    bridge.jogXyTable("x", 1)
    assert bridge.xyPosX == "10.00"
    bridge.jogXyTable("x", -1)
    assert bridge.xyPosX == "0.00"
    # Jog must clamp to the real table bound, never walk past it.
    for _ in range(200):
        bridge.jogXyTable("x", 1)
    assert float(bridge.xyPosX) == 1200.0, "jog must clamp at the real configured width, not overshoot"

    bridge.disableXyTable()
    assert bridge.xyHasTable is False

    # --- rack manager: real reset-resets-BOTH-racks quirk, real
    # capacity/slot/type/pos mutation ---
    assert bridge.rackSelectedRobotId == "x1"
    assert bridge.rackEnabled is False, "default_rack_system() starts disabled until enabled"
    bridge.enableRackSystem()
    assert bridge.rackEnabled is True
    rack_robot = bridge._rack_selected_robot()
    rack_robot.rack_system["rack1"]["type"] = "Input"
    rack_robot.rack_system["rack2"]["type"] = "Output"
    rack_robot.set_rack_system(rack_robot.rack_system)
    data = {r["rackId"]: r for r in bridge.rackData}
    assert data["rack1"]["type"] == "Input" and data["rack2"]["type"] == "Output"
    assert data["rack1"]["active"] is True and len(data["rack1"]["slots"]) == data["rack1"]["capacity"]

    assert data["rack1"]["slots"][0] is True, "default_rack()'s own real usableSlots default is all-True"
    bridge.toggleRackSlot("rack1", 0)
    data = {r["rackId"]: r for r in bridge.rackData}
    assert data["rack1"]["slots"][0] is False
    bridge.setRackCapacity("rack1", 5)
    assert {r["rackId"]: r for r in bridge.rackData}["rack1"]["capacity"] == 5
    bridge.setRackPos("rack1", "j2", 45.5)
    assert {r["rackId"]: r for r in bridge.rackData}["rack1"]["pos"]["j2"] == 45.5

    # The real, deliberately-preserved quirk: Reset (from EITHER rack's
    # own button - both call the same Slot) resets BOTH racks back to
    # their real defaults, discarding rack2's own "Output" type too.
    bridge.setRackType("rack2", "None")  # change rack2 away from its real default, to prove Reset overwrites it back
    bridge.resetRackSystem()
    data = {r["rackId"]: r for r in bridge.rackData}
    assert data["rack1"]["type"] == "Input" and data["rack2"]["type"] == "Output", "default_rack_system()'s own real seed: rack1=Input, rack2=Output"
    assert data["rack1"]["capacity"] == RACK_MAX_CAPACITY, "Reset must discard the capacity=5 set earlier too"
    assert bridge.rackEnabled is True, "Reset force-sets enabled True even if it already was"

    bridge.disableRackSystem()
    assert bridge.rackEnabled is False

    # --- pick and place: PnP-only path (the Machine combo never offers a
    # 3rd type in practice - see qt_suite.py's own __init__ comment on the
    # unported size-only branch), real 5-axis mutation + reset, real
    # per-machine-type independent module block ---
    assert bridge.pnpSelectedRobotId == "x1"
    assert bridge.pnpMachineType == "juanenPnP"
    assert bridge.pnpEnabled is False, "no juanenPnP module on this robot yet"
    bridge.enablePnp()
    assert bridge.pnpEnabled is True

    axes = {a["field"]: a for a in bridge.pnpAxisData}
    assert axes["axisX"]["min"] == 0 and axes["axisX"]["max"] == 433, "real fixed hardware bound from PNP_AXES"
    assert axes["nozzle1Rotation"]["min"] == -180 and axes["nozzle1Rotation"]["max"] == 180
    assert all(a["value"] == 0 for a in bridge.pnpAxisData)

    bridge.setPnpAxis("axisX", 250)
    bridge.setPnpAxis("nozzle1Rotation", -90)
    axes = {a["field"]: a for a in bridge.pnpAxisData}
    assert axes["axisX"]["value"] == 250 and axes["nozzle1Rotation"]["value"] == -90

    bridge.resetPnp()
    assert bridge.pnpEnabled is True, "resetPnp force-enables, matching _on_reset()'s own module['enabled'] = True"
    assert all(a["value"] == 0 for a in bridge.pnpAxisData), "reset must clear the axes set just above"

    # Switching machine type is its own independent selection - lumenPnP
    # has its own separate module block, untouched by juanenPnP's above.
    bridge.selectPnpMachine("lumenPnP")
    assert bridge.pnpMachineType == "lumenPnP"
    assert bridge.pnpMachineLabel == "LumenPnP"
    assert bridge.pnpEnabled is False, "lumenPnP's own module block was never enabled"

    bridge.selectPnpMachine("juanenPnP")
    assert bridge.pnpEnabled is True, "juanenPnP's own module block survived the round trip through lumenPnP"
    bridge.disablePnp()
    assert bridge.pnpEnabled is False

    # --- kinematic brain stage: CONTROLLER-level (no robot selector at
    # all, unlike every panel above) - real default seed + mutation
    # across every sub-widget. Already fed by the same fake_state_xy
    # active_state_changed emission above (every _on_*_state_changed
    # hook on this bridge listens to that one real signal). ---
    assert bridge.kbsHasController is True
    axes = {a["axis"]: a for a in bridge.kbsAxisData}
    assert axes["x"]["value"] == "0.00" and axes["z"]["value"] == "0.00"
    assert bridge.kbsTableWidth == 600 and bridge.kbsTableLength == 400 and bridge.kbsTableHeight == 150, "default_kinematic_brain_stage()'s own real seed"

    bridge.setKbsJogStep(50.0)
    bridge.jogKbsAxis("x", 1)
    axes = {a["axis"]: a for a in bridge.kbsAxisData}
    assert axes["x"]["value"] == "50.00"
    for _ in range(20):  # jog must clamp at the real configured width, never overshoot
        bridge.jogKbsAxis("x", 1)
    axes = {a["axis"]: a for a in bridge.kbsAxisData}
    assert axes["x"]["value"] == "600.00"

    bridge.setKbsTableSize("width", 800)
    assert bridge.kbsTableWidth == 800

    assert bridge.kbsTherm1 == "24.0°C" and bridge.kbsTherm2 == "24.0°C", "real default sensor seed"
    assert bridge.kbsTargetTemp == 0
    bridge.setKbsTargetTemp(60)
    assert bridge.kbsTargetTemp == 60
    assert bridge.kbsSsrOn is False
    bridge.toggleKbsSsr()
    assert bridge.kbsSsrOn is True

    assert bridge.kbsAtcIndex == 1 and bridge.kbsToolCount == 6 and bridge.kbsHomed is False
    bridge.stepKbsAtc(1)
    assert bridge.kbsAtcIndex == 2 and bridge.kbsHomed is True, "stepping always sets homed True, matching _on_atc_step()'s own real behavior"
    bridge.stepKbsAtc(-1)
    assert bridge.kbsAtcIndex == 1

    bridge.setKbsToolCount(4)
    assert bridge.kbsToolCount == 4
    bridge.stepKbsAtc(-1)  # currentIndex 0 -> -1 -> real negative-wraparound branch -> toolCount-1 = 3, displayed as 4
    assert bridge.kbsAtcIndex == 4

    assert bridge.kbsConveyorInstalled is False
    bridge.installKbsConveyor()
    assert bridge.kbsConveyorInstalled is True
    assert bridge.kbsConveyorRunning is False
    bridge.toggleKbsConveyorRun()
    assert bridge.kbsConveyorRunning is True
    bridge.setKbsConveyorSpeed(75)
    assert bridge.kbsConveyorSpeed == 75

    endstops = {e["key"]: e for e in bridge.kbsEndstopData}
    assert len(endstops) == 12 and endstops["xMin"]["active"] is False
    bridge.toggleKbsEndstop("xMin")
    endstops = {e["key"]: e for e in bridge.kbsEndstopData}
    assert endstops["xMin"]["active"] is True

    assert bridge.kbsFans == [False, False, False]
    assert len(bridge.kbsPumps) == 10 and len(bridge.kbsValves) == 10
    bridge.toggleKbsFan(1)
    assert bridge.kbsFans == [False, True, False]
    bridge.toggleKbsPump(9)
    assert bridge.kbsPumps[9] is True
    bridge.toggleKbsValve(0)
    assert bridge.kbsValves[0] is True

    # --- module config (CNC/Laser/HeatedBed/VacuumTable): one generic
    # bridge implementation dispatches on activePanel, mirroring
    # module_config_panel.py's own ModuleConfigPanel(module_key, ...)
    # parameterization - real per-nav-key independent robot selection,
    # real enable/disable/size/reset, real "extra" shapes ---
    bridge.navigatePanel("cnc")
    assert bridge.moduleSelectedRobotId == "x1"
    assert bridge.moduleMachineName == "JuanenCNC"
    assert bridge.moduleEnabled is False
    assert bridge.moduleWidth == 500 and bridge.moduleLength == 500, "display fallback before any real module exists"
    bridge.enableModuleConfig()
    assert bridge.moduleEnabled is True
    bridge.setModuleWidth(900)
    bridge.setModuleLength(700)
    assert bridge.moduleWidth == 900 and bridge.moduleLength == 700
    bridge.resetModuleConfig()
    assert bridge.moduleWidth == 500 and bridge.moduleLength == 500, "CNC resets to the same 500mm as its own display fallback"
    assert bridge.moduleEnabled is True, "Reset force-enables, matching _on_reset()'s own real payload"

    # A different nav key is a genuinely separate module block AND a
    # genuinely separate robot selection cache, never shared with CNC's.
    bridge.navigatePanel("laser")
    assert bridge.moduleMachineName == "JuanenLaser"
    assert bridge.moduleEnabled is False, "laser's own module block was never touched by the CNC section above"

    bridge.navigatePanel("heated_bed")
    assert bridge.moduleExtraKind == "heated_bed"
    assert bridge.moduleEnabled is False
    bridge.enableModuleConfig()
    assert bridge.moduleTargetTemp == 60 and bridge.moduleTherm1 == "25.0 °C" and bridge.moduleTherm2 == "25.0 °C", "real extra defaults set on first Enable"
    assert bridge.moduleSsrOn is False
    bridge.setModuleTargetTemp(80)
    bridge.toggleModuleSsr()
    assert bridge.moduleTargetTemp == 80 and bridge.moduleSsrOn is True
    bridge.resetModuleConfig()
    assert bridge.moduleTargetTemp == 60 and bridge.moduleSsrOn is False, "Reset writes the same real extra defaults back"
    assert bridge.moduleWidth == 500 and bridge.moduleLength == 500, "HeatedBed resets to 500mm too, same as CNC/Laser"

    bridge.navigatePanel("vacuum_table")
    assert bridge.moduleExtraKind == "vacuum_table"
    assert bridge.moduleWidth == 500, "display fallback is 500mm - same as every other module, before Reset ever runs"
    bridge.enableModuleConfig()
    assert bridge.modulePumpOn is False and bridge.moduleValveOn is False
    bridge.toggleModulePump()
    bridge.toggleModuleValve()
    assert bridge.modulePumpOn is True and bridge.moduleValveOn is True
    bridge.resetModuleConfig()
    # The real, if minor, inconsistency this panel's own header documents:
    # VacuumTable DISPLAYS the same 500mm fallback as every other module
    # but its own Reset writes 100mm, a genuinely different number.
    assert bridge.moduleWidth == 100 and bridge.moduleLength == 100, "VacuumTable's own real reset-vs-display mismatch"
    assert bridge.modulePumpOn is False and bridge.moduleValveOn is False, "Reset also clears the extra pump/valve state"

    # --- ATC Tools: NOT built on the generic Module Config shape (real,
    # fundamentally different shape - None vs a full ATCConfig, no
    # separate enabled flag, 3 layout modes) - own real robot selection,
    # real type/grid/revolver mutation, real per-slot AND base-pickup
    # position editing, real JSON round-trip validation ---
    bridge.navigatePanel("atc")
    assert bridge.atcSelectedRobotId == "x1"
    assert bridge.atcConfigured is False
    assert bridge.atcSlotsData == [], "no ATC config yet - _default_atc_config() is a DISPLAY-only fallback, never written until Enable"
    bridge.enableAtc()
    assert bridge.atcConfigured is True
    assert bridge.atcType == "vertical_panel" and bridge.atcIsPanel is True
    assert bridge.atcPanelGrid == "2x2"
    assert len(bridge.atcSlotsData) == 4, "2x2 grid = 4 real slots"
    assert all(s["tool"] == "None" for s in bridge.atcSlotsData)

    bridge.setAtcTool(1, "Drill (BL4260)")
    slots = {s["slot"]: s for s in bridge.atcSlotsData}
    assert slots[1]["tool"] == "Drill (BL4260)" and slots[1]["toolIndex"] == URTC_TOOLS.index("Drill (BL4260)")
    assert slots[0]["tool"] == "None", "only the touched slot changed"

    bridge.toggleAtcSlotPos(1)
    slots = {s["slot"]: s for s in bridge.atcSlotsData}
    assert slots[1]["editing"] is True and len(slots[1]["pos"]) == 6, "6 joint fields, no table fields - this robot has no XY table"
    bridge.setAtcPosField("1", "j2", 45.0)
    slots = {s["slot"]: s for s in bridge.atcSlotsData}
    pos_j2 = next(f for f in slots[1]["pos"] if f["field"] == "j2")
    assert pos_j2["value"] == 45.0
    bridge.toggleAtcSlotPos(1)
    assert {s["slot"]: s for s in bridge.atcSlotsData}[1]["editing"] is False

    bridge.setAtcPanelGrid("3x3")
    assert bridge.atcPanelGrid == "3x3" and len(bridge.atcSlotsData) == 9
    assert all(s["tool"] == "None" for s in bridge.atcSlotsData), "changing the grid clears all tool assignments, matching _on_grid_changed()'s own real behavior"

    bridge.setAtcType("revolver")
    assert bridge.atcIsPanel is False
    assert bridge.atcRevolverSlots == 8
    assert len(bridge.atcSlotsData) == 8
    assert all(not s["showPosButton"] for s in bridge.atcSlotsData), "no per-slot position editor in revolver mode"
    bridge.setAtcRevolverSlots(5)
    assert bridge.atcRevolverSlots == 5 and len(bridge.atcSlotsData) == 5

    assert bridge.atcBaseEditing is False
    bridge.toggleAtcBasePos()
    assert bridge.atcBaseEditing is True
    bridge.setAtcPosField("revolver", "j1", -90.0)
    base_j1 = next(f for f in bridge.atcBasePos if f["field"] == "j1")
    assert base_j1["value"] == -90.0

    bridge.resetAtc()
    assert bridge.atcType == "vertical_panel" and bridge.atcPanelGrid == "2x2", "Reset writes the same real _default_atc_config() Enable does"
    assert bridge.atcConfigured is True

    bridge.disableAtc()
    assert bridge.atcConfigured is False
    assert bridge.atcSlotsData == []

    # A real, honest JSON round-trip: save what Enable wrote, then load it
    # back on a config Reset already diverged from, confirming the file
    # (not just in-memory state) round-trips correctly.
    bridge.enableAtc()
    bridge.setAtcTool(0, "Vacuum / Pneumatic Gripper")
    atc_tmp_path = tempfile.mktemp(suffix=".json")
    bridge.saveAtcConfig(atc_tmp_path)
    bridge.setAtcType("revolver")
    assert bridge.atcType == "revolver"
    bridge.loadAtcConfig(atc_tmp_path)
    assert bridge.atcLoadError == ""
    assert bridge.atcType == "vertical_panel", "real file round-trip restored the saved type"
    assert {s["slot"]: s for s in bridge.atcSlotsData}[0]["tool"] == "Vacuum / Pneumatic Gripper"
    os.remove(atc_tmp_path)

    # Real, honest validation - matches _on_load_config()'s own QMessageBox.warning()
    bad_path = tempfile.mktemp(suffix=".json")
    with open(bad_path, "w", encoding="utf-8") as f:
        f.write('{"no_type_field": true}')
    bridge.loadAtcConfig(bad_path)
    assert bridge.atcLoadError != "", "a config missing the required type key must be rejected, not silently accepted"
    os.remove(bad_path)

    # --- Cameras: real metadata + type/source/robot mutation, real
    # discovery/PTZ/status wiring against a real HydraConnection (only
    # the network transport is stubbed - iter_mjpeg_frames() itself has
    # its own dedicated real test, verify_mjpeg_stream.py) ---
    bridge.addManualServer("10.0.0.9", 3000, "admin", "hunter2")
    cam_conn_id = bridge.serverRows[0]["connId"]
    cam_conn = controller.connections[cam_conn_id]
    cam_conn.state = HydraState({
        "activeControllerId": "c1",
        "controllers": [{
            "id": "c1",
            "robots": [{"id": 5, "model": "AR3", "role": "Idle"}],
            "cameras": [
                {"id": 1, "connected": False, "type": "USB Vision Camera", "sourceType": "usb"},
                {"id": 2, "connected": False, "type": "IP Vision Camera Main Stream", "sourceType": "ip",
                 "ipHost": "192.168.0.211", "rtspPort": 554, "rtspPath": "/11", "discoveredStreamPaths": ["/11", "/12"]},
            ],
        }],
    })
    cameras = {c["id"]: c for c in bridge.camerasData}
    assert set(cameras) == {1, 2}
    assert cameras[1]["sourceType"] == "usb" and cameras[1]["isIp"] is False
    assert cameras[2]["isIp"] is True and cameras[2]["typeOptions"][:2] == ["IP Vision Camera Main Stream", "IP Vision Camera Sub Stream"], "real 2-path ip_stream_labels()"
    assert cameras[2]["extraPaths"] == [{"label": "IP Vision Camera Sub Stream", "value": "/12", "index": 1}]
    robot_opts = {r["id"]: r["label"] for r in bridge.cameraRobotOptions}
    assert robot_opts[""] != "" and "5" in robot_opts, "the real None/Floating option plus every real robot"

    bridge.setCameraAssignedRobot(1, "5")
    assert {c["id"]: c for c in bridge.camerasData}[1]["assignedRobotId"] == "5"
    bridge.setCameraField(1, "hardware_source", "/dev/video2")
    assert {c["id"]: c for c in bridge.camerasData}[1]["hardwareSource"] == "/dev/video2"
    bridge.setCameraType(2, "IP Vision Camera Sub Stream")
    cam2 = {c["id"]: c for c in bridge.camerasData}[2]
    assert cam2["cameraType"] == "IP Vision Camera Sub Stream"
    assert cam2["rtspPath"] == "/12", "real re-point per _on_type_combo_changed()'s own behavior - picking Sub Stream re-points rtsp_path at its own real discovered path"
    bridge.setCameraExtraPath(2, 1, "/13")
    cam2 = {c["id"]: c for c in bridge.camerasData}[2]
    assert cam2["extraPaths"][0]["value"] == "/13" and cam2["rtspPath"] == "/13", "editing the ACTIVE stream's own extra path field must also update rtsp_path itself"
    bridge.setCameraSourceType(1, "ip")
    cam1 = {c["id"]: c for c in bridge.camerasData}[1]
    assert cam1["sourceType"] == "ip" and cam1["cameraType"] == "IP Vision Camera Main Stream", "auto-normalized off the stale USB type on a source-type toggle"

    # Real discovery/status/PTZ - only the network transport stubbed.
    async def _fake_discover_usb():
        return 200, {"devices": [{"index": 0, "available": True, "width": 640, "height": 480}]}

    async def _fake_discover_rtsp(host, port, username, password):
        return 200, {"ok": True, "paths": ["/21", "/22"], "triedPaths": ["/21", "/22"]}

    async def _fake_camera_status():
        return 200, {"c1:1": {"status": "running", "lastError": None}, "c1:2": {"status": "error", "lastError": "connection refused"}}

    ptz_calls = []

    async def _fake_send_ptz(camera_id, host, username, password, pan, tilt, zoom):
        ptz_calls.append((camera_id, host, username, password, pan, tilt, zoom))
        return 200, {"ok": True}

    cam_conn.discover_usb_devices = _fake_discover_usb
    cam_conn.discover_rtsp_path = _fake_discover_rtsp
    cam_conn.fetch_camera_status = _fake_camera_status
    cam_conn.send_ptz = _fake_send_ptz

    loop.run_until_complete(bridge._run_discover_usb(1, cam_conn))
    assert {c["id"]: c for c in bridge.camerasData}[1]["usbDevices"] == [{"label": "/dev/video0 (640x480)", "value": 0}]
    bridge.pickUsbDevice(1, 0)
    assert {c["id"]: c for c in bridge.camerasData}[1]["hardwareSource"] == ("0" if sys.platform == "win32" else "/dev/video0")

    loop.run_until_complete(bridge._run_discover_rtsp(2, cam_conn, "192.168.0.211", 554, "admin", "admin123456"))
    cam2 = {c["id"]: c for c in bridge.camerasData}[2]
    assert cam2["rtspPath"] == "/21" and cam2["cameraType"] == "IP Vision Camera Main Stream", "a fresh discovery resets to real Main"

    loop.run_until_complete(bridge._poll_camera_status())
    frames = {f["id"]: f for f in bridge.cameraFrameVersions}
    assert frames[1]["statusText"] != "" and frames[2]["statusColor"] == "#ef4444", "real per-camera status badge, error state included"

    cam2_model = cam_conn.state.active_controller.cameras[1]
    cam2_model.set_ip_host("192.168.0.211")
    loop.run_until_complete(bridge._run_ptz(2, 60, 0, 0))
    assert ptz_calls == [(2, "192.168.0.211", "", "", 60, 0, 0)], "PTZ must forward THIS camera's own real host/credentials"
    assert {c["id"]: c for c in bridge.camerasData}[2]["ptzError"] == ""

    async def _fake_send_ptz_fail(camera_id, host, username, password, pan, tilt, zoom):
        return 200, {"ok": False, "error": "no motorized PTZ hardware"}

    cam_conn.send_ptz = _fake_send_ptz_fail
    loop.run_until_complete(bridge._run_ptz(2, 0, 60, 0))
    assert {c["id"]: c for c in bridge.camerasData}[2]["ptzError"] == "no motorized PTZ hardware"

    bridge.removeServer(cam_conn_id)

    # --- Flasher: 2 real, separate instances (urtc_flasher/hydra_flasher),
    # real tier-enable gating, real per-instance robot selection, the
    # real can_ota.py mock query/flash generators (not faked - only the
    # random 5% "offline" branch in mock_query_version() is stubbed, to
    # keep this test deterministic; mock_flash()'s own small anti-
    # rollback random chance is avoided for real by setting
    # allow_downgrade, which genuinely skips that branch), and real
    # GitHub fetch/download with only the network transport stubbed ---
    flasher_state = HydraState({
        "activeControllerId": "c1",
        "controllers": [{
            "id": "c1", "name": "Cell One",
            "robots": [
                {"id": "x1", "model": "AR3", "urtcConnected": True},
                {"id": "x2", "model": "AR2", "urtcConnected": False},
            ],
        }],
    })
    controller.active_state_changed.emit(flasher_state)

    bridge.navigatePanel("urtc_flasher")
    tiers = {t["key"]: t for t in bridge.flasherTierOptions}
    assert set(tiers) == {"urtcHead", "urtcExpansion"}
    assert bridge.flasherSelectedRobotId == "x1", "first real robot, matches every other panel's own restore-or-first logic"
    assert tiers["urtcHead"]["enabled"] is True, "x1's own urtcConnected is True"
    assert tiers["urtcExpansion"]["enabled"] is False, "no expansionBoardType configured yet"

    bridge.selectFlasherRobot("x2")
    tiers = {t["key"]: t for t in bridge.flasherTierOptions}
    assert tiers["urtcHead"]["enabled"] is False, "x2's own urtcConnected is False"

    bridge.navigatePanel("hydra_flasher")
    hydra_tiers = {t["key"]: t for t in bridge.flasherTierOptions}
    assert set(hydra_tiers) == {"kinematicBrain", "controllerBoard"}
    assert bridge.flasherNeedsRobotSlot is False, "kinematicBrain is the real default tier - controller-level, no robot slot"
    assert bridge.flasherSelectedRobotId == "x1", "hydra_flasher's own robot selection is genuinely separate - still x1, untouched by the x2 switch on urtc_flasher above"

    bridge.selectFlasherTier("controllerBoard")
    assert bridge.flasherNeedsRobotSlot is True
    assert "A1" in bridge.flasherHopDescription and "STM32G474RET6" in bridge.flasherHopDescription, "real hop_description() text - controller -> SPI -> STM32H745 -> FDCAN1 -> slot label (chip)"

    async def _fake_query_online(target):
        return VersionQueryResult(online=True, firmware_version="0.1.2", bootloader_version="0.0.1", hardware_id="RCB-001")

    qs.mock_query_version = _fake_query_online
    target = bridge._flasher_target("hydra_flasher")
    assert target is not None
    loop.run_until_complete(bridge._run_flasher_query("hydra_flasher", target))
    assert "0.1.2" in bridge.flasherVersionLabel
    assert any("0.1.2" in e["text"] for e in bridge.flasherLog)

    fw_path = tempfile.mktemp(suffix=".bin")
    with open(fw_path, "wb") as f:
        f.write(b"\x00" * 4096)
    bridge.browseFlasherFile(fw_path)
    assert "0x" in bridge.flasherFileInfo and "4.0 KB" in bridge.flasherFileInfo
    os.remove(fw_path)

    fake_asset = GithubFirmwareAsset(name="rcb_v2.bin", url="https://example.invalid/rcb_v2.bin", size=8192, release_tag="2.0.0", published_at="", chip="STM32G474RET6", hardware_id="0x48374334")

    async def _fake_fetch_releases(repo, tier, branch="main"):
        return [fake_asset]

    downloaded = {}

    async def _fake_download(asset):
        downloaded["asset"] = asset
        return b"\x11" * 8192

    qs.fetch_github_firmware_releases = _fake_fetch_releases
    qs.download_github_firmware = _fake_download
    bridge.fetchFlasherGithub()
    loop.run_until_complete(asyncio.sleep(0))
    assert len(bridge.flasherGithubAssets) == 1 and "rcb_v2.bin" in bridge.flasherGithubAssets[0]["label"]
    bridge.useFlasherGithubAsset(0)
    loop.run_until_complete(asyncio.sleep(0))
    assert downloaded["asset"] is fake_asset
    assert "rcb_v2.bin" in bridge.flasherFileInfo

    bridge.setFlasherAllowDowngrade(True)
    target = bridge._flasher_target("hydra_flasher")
    file = bridge._flasher_file["hydra_flasher"]
    loop.run_until_complete(bridge._run_flash("hydra_flasher", target, file))
    assert bridge.flasherProgressPercent == 100
    assert any(e["text"] == "Flash complete" and e["level"] == "ok" for e in bridge.flasherLog), "the real translated LBL_FLASH_DONE message, ok level"
    board = bridge._flasher_board_state("hydra_flasher")
    assert board.get("firmwareVersion") == "rcb_v2", "real .bin suffix stripped, matches _flasher_apply_patch()'s own real behavior"

    # Real hardware-unreachable gating: urtcExpansion has no real relay
    # tunnel yet (resolve_hardware_target() returns None for it) - matches
    # can_ota.py's own honest boundary, not something invented here.
    hw_state = HydraState({
        "settings": {"canOta": {"transport": "hardware"}},
        "activeControllerId": "c1",
        "controllers": [{"id": "c1", "name": "Cell One", "robots": [{"id": "x1", "model": "AR3", "urtcConnected": True}]}],
    })
    controller.active_state_changed.emit(hw_state)
    bridge.navigatePanel("urtc_flasher")
    bridge.selectFlasherTier("urtcExpansion")
    assert bridge.flasherUnreachable is True

    # --- Tester: deliberately duplicates Flasher's own target-selection
    # shape (real, separate _tester_* state) - real tier/robot gating,
    # real global LED/OLED/F-RAM local state, real per-tool telemetry
    # category, the real can_ota.py mock_self_test()/mock_bus_monitor()
    # generators (not faked - both have genuine per-step randomness, so
    # only structural/label assertions are made, never an exact pass/fail
    # or frame content) ---
    tester_state = HydraState({
        "activeControllerId": "c1",
        "controllers": [{
            "id": "c1", "name": "Cell One",
            "robots": [
                {"id": "x1", "model": "AR3", "urtcConnected": True, "tool": "Drill (BL4260)"},
                {"id": "x2", "model": "AR2", "urtcConnected": False},
            ],
        }],
    })
    controller.active_state_changed.emit(tester_state)

    bridge.navigatePanel("urtc_tester")
    t_tiers = {t["key"]: t for t in bridge.testerTierOptions}
    assert set(t_tiers) == {"urtcHead", "urtcExpansion"}
    assert bridge.testerSelectedRobotId == "x1"
    assert t_tiers["urtcHead"]["enabled"] is True and t_tiers["urtcExpansion"]["enabled"] is False
    assert bridge.testerRobotOptions[0]["label"] == "A1 - AR3", "no (unreachable) suffix here - the real classic Tester combo never adds one, unlike Flasher's own"
    assert bridge.testerSimulatedNoteVisible is False, "transport is real mock here"

    assert bridge.testerShowGlobal is True, "urtcHead is the real default tier for URTC_TIERS"
    assert bridge.testerShowFram is True
    assert bridge.testerShowTelemetry is True
    assert bridge.testerTelemetryTitle == "Tool Telemetry - Drill (BL4260)"
    assert bridge.testerTelemetryLabel != "" and "LBL_TELEMETRY" not in bridge.testerTelemetryLabel, "a real translated category label, not the raw key"

    bridge.setTesterStatusColor("#ff00aa")
    assert bridge.testerStatusColor == "#ff00aa"
    assert bridge.testerRingOn is False
    bridge.toggleTesterRing()
    assert bridge.testerRingOn is True
    bridge.setTesterOledMode("night")
    assert bridge.testerOledMode == "night"

    assert bridge.testerFramStateLabel == "Unknown - query to check"
    loop.run_until_complete(bridge._run_tester_fram_query("urtc_tester"))
    assert bridge.testerFramStateLabel in ("Valid saved state found", "No saved state")
    bridge.testerFramErase()
    assert bridge.testerFramStateLabel == "No saved state"

    target = bridge._tester_target("urtc_tester")
    assert target is not None
    loop.run_until_complete(bridge._run_tester_self_test("urtc_tester", target))
    steps = bridge.testerSelfTestSteps
    assert len(steps) == 5, "real urtcHead step set: comm, version, fram, tool, telemetry"
    assert all(s["label"] != "" for s in steps)
    assert bridge.testerTesting is False

    bridge.toggleTesterMonitor()
    assert bridge.testerMonitorRunning is True
    loop.run_until_complete(asyncio.sleep(0.35))  # mock_bus_monitor's own first real frame lands ~0.2s in
    assert len(bridge.testerFrames) >= 1
    frame = bridge.testerFrames[0]
    assert frame["id"].startswith("0x") and frame["dlc"] in (2, 4)
    bridge.toggleTesterMonitor()
    assert bridge.testerMonitorRunning is False
    loop.run_until_complete(asyncio.sleep(0))  # let the real task.cancel() above actually propagate

    # Switching tier/robot must drop any in-flight self-test/monitor state
    # for the PREVIOUS target - matches _reset_for_new_target()'s own
    # real behavior.
    bridge.selectTesterTier("urtcExpansion")
    assert bridge.testerSelfTestSteps == [] and bridge.testerFrames == []

    bridge.navigatePanel("hydra_tester")
    assert bridge.testerSelectedRobotId == "x1", "hydra_tester's own robot selection is genuinely separate from urtc_tester's"
    hydra_t_tiers = {t["key"]: t for t in bridge.testerTierOptions}
    assert set(hydra_t_tiers) == {"kinematicBrain", "controllerBoard"}
    assert bridge.testerNeedsRobotSlot is False, "kinematicBrain is the real default tier"

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

    # --- robot control: correct real command routing. The full
    # optimistic-mutation pipeline (local_mutate applying against a
    # robot looked up fresh from HydraConnection's OWN internal state)
    # is HydraConnection.send_command's own real surface, not this
    # bridge's - so this checks the bridge's own real responsibility
    # instead: does it call SuiteController.send_robot_command with the
    # right robot id/command/params, exactly matching
    # robot_control.py's own real _on_joint_changed/_on_speed_changed/
    # _on_accel_changed calls? A recording stub replaces the real
    # method for this (no real HydraConnection needed either way, since
    # there is no active one here). ---
    assert bridge.selectedRobotId == "r1", "the first robot becomes selected automatically"
    assert bridge.canControlRobot is True
    joints_before = {j["name"]: j["value"] for j in bridge.selectedRobotJoints}
    assert joints_before == {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}

    calls = []
    controller.send_robot_command = lambda *a, **kw: calls.append((a, kw))

    bridge.setJoint("j1", 45.0)
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == "r1" and args[1] == "jog"
    assert args[2]["joints"]["j1"] == 45.0 and args[2]["target"] == "robot"
    assert kwargs.get("debounce_ms") == 50 or (len(args) > 4 and args[4] == 50)

    calls.clear()
    bridge.setRobotSpeed(150)
    assert len(calls) == 1 and calls[0][0][0] == "r1" and calls[0][0][1] == "speed"
    assert calls[0][0][2] == {"speed": 150}

    calls.clear()
    bridge.setRobotAcceleration(77)
    assert len(calls) == 1 and calls[0][0][2] == {"acceleration": 77}

    bridge.selectRobot("r2")
    assert bridge.selectedRobotId == "r2"
    assert bridge.canControlRobot is True
    bridge.selectRobot("does-not-exist")
    assert bridge.canControlRobot is False, "selecting an unknown id must not silently keep the old robot armed"

    # --- trajectory: real point record/apply/delete against the real
    # RobotView (push_active_state is stubbed the same way
    # send_robot_command was above - HydraConnection.push_state()'s own
    # network half is not this bridge's surface either) ---
    bridge.selectRobot("r1")
    assert bridge.trajectoryPoints == []
    bridge.recordTrajectoryPoint()
    assert len(bridge.trajectoryPoints) == 1
    assert bridge.trajectoryPoints[0]["joints"] == "0.0 / 0.0 / 0.0 / 0.0 / 0.0 / 0.0"
    bridge.setJoint("j2", 30.0)  # local_mutate never actually applied (stubbed above) - set the raw dict directly instead
    bridge._selected_robot().raw["joints"] = {**bridge._selected_robot().raw.get("joints", {}), "j2": 30.0}
    bridge.recordTrajectoryPoint()
    assert len(bridge.trajectoryPoints) == 2
    assert "30.0" in bridge.trajectoryPoints[1]["joints"]

    push_calls = []
    controller.push_active_state = lambda: push_calls.append(True)
    bridge.applyTrajectoryPoint(0)  # point 0 was recorded before the j2=30 edit -> j2 back to 0.0
    assert len(push_calls) == 1
    assert bridge._selected_robot().raw["joints"]["j2"] == 0.0

    bridge.deleteTrajectoryPoint(0)
    assert len(bridge.trajectoryPoints) == 1

    # Switching the selected robot resets recorded points - matches
    # trajectory_panel.py's own set_selected_robot exactly.
    bridge.selectRobot("r2")
    assert bridge.trajectoryPoints == [], "switching robots must reset recorded trajectory points"

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
