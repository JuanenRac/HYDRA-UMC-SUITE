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
from hydra_suite.models import RACK_MAX_CAPACITY, HydraState
from hydra_suite.ui.nav_sidebar import ALL_DOCK_KEYS
from hydra_suite.ui.panels.admin_server_panel import _format_uptime
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
