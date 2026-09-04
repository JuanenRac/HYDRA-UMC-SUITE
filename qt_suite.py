# =============================================================================
# HYDRA-UMC SUITE - qt_suite.py (Qt Quick command-deck entry point)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Qt Quick front end for HYDRA-UMC SUITE - the real "redesign from zero"
this repo's own CHANGELOG.md documents as necessary after BOTH real ways of
embedding QML inside the established QMainWindow+QDockWidget tree proved
unsafe (QQuickWidget painted solid black; QQuickView+createWindowContainer
rendered correctly in isolation but corrupted sibling widgets' real Z-order
inside this app's actual 26-dock layout - see this session's own memory
note for the full account). This is a STANDALONE pure-QML
ApplicationWindow instead, the same real shape as
HYDRA-UMC-OS-REBUILDER/HYDRA-UMC-UPDATER/URTC-TESTER/URTC-FLASHER (all of
which already render correctly) - not an embed, so the mixing problem
those two failed attempts hit doesn't apply here at all.

Navigation trades QDockWidget's float/split/tab-merge flexibility for
HYDRA-UMC-STUDIO's own simpler nav-sidebar-plus-single-content-pane shape
(nav_sidebar.py's own real taxonomy - ROOT_ITEMS/INDUSTRIAL_ITEMS/
URTC_ITEMS/HYDRA_ITEMS/HYDRA_ECOSYSTEM_ITEMS - is mirrored here item for
item) - a deliberate real design choice per the STUDIO<->SUITE parity
rule, not an oversight: most users never actually float/split these docks,
and a hand-built docking system in QML would be a second, much bigger real
engineering project of its own (see e.g. KDDockWidgets existing as a whole
separate library for exactly this reason).

hydra_suite.app.SuiteController is reused completely unchanged here - it
was already a plain QObject with Qt Signals, never tied to QtWidgets, so
it needs zero changes to serve a QML front end too.

REAL, HONEST STATUS (kept current in this repo's own CHANGELOG.md, the
authoritative source - this docstring is not re-updated per panel to avoid
drifting out of sync with it): only a subset of the 26 real panels
main_window.py docks are ported to actual QML content so far; every other
one shows a real, honest "not yet migrated" placeholder (never a fake,
empty-but-styled panel pretending to be done) pointing back at the
existing classic view, which remains fully functional and is still this
app's own default entry point. Run `python main.py --qtquick` to see this
one instead - exactly the same opt-in convention URTC-TESTER/URTC-FLASHER
used while THEY were mid-migration.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import qasync
from PySide6.QtCore import Property, QDateTime, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from hydra_suite import __version__, logging_handler
from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import JOINT_NAMES, HydraState, RobotView, ServerInfo
from hydra_suite.net.discovery import DEFAULT_PORT, discover_servers
from hydra_suite.ui.panels.admin_clients_panel import _relative_duration
from hydra_suite.ui.panels.admin_logs_panel import _extract_tag
from hydra_suite.ui.panels.admin_server_panel import _format_uptime
from hydra_suite.ui.panels.ai_family_status_panel import AI_FAMILIES
from hydra_suite.ui.panels.ecosystem_services_panel import _HEALTH_COLOR, _STACK_COLOR, _badge_label, _health
from hydra_suite.ui.panels.ecosystem_telemetry_panel import _AGGREGATES, _RANGE_PRESETS
from hydra_suite.ui.panels.xy_table_panel import (
    _DISPLAY_DEFAULT_SIZE_MM as _XY_DISPLAY_DEFAULT_SIZE_MM,
    JOG_STEPS_MM as _XY_JOG_STEPS_MM,
    _default_xy_table,
)
from hydra_suite.ui.panels.server_browser import STATUS_DISPLAY_KEYS

IMAGES_DIR = Path(__file__).resolve().parent / "images"
QML_PATH = Path(__file__).resolve().parent / "assets" / "qml" / "Main.qml"

# Real taxonomy - kept in exact lockstep with nav_sidebar.py's own
# ROOT_ITEMS/INDUSTRIAL_ITEMS/URTC_ITEMS/HYDRAUMC_ITEMS/
# HYDRAUMC_ECOSYSTEM_ITEMS (that file's own real test,
# tests/test_nav_sidebar.py, already guards against those drifting from
# main_window.py's own dock keys - this constant is a second, independent
# real transcription of the SAME source of truth for the QML nav, not a
# third invented taxonomy).
from hydra_suite.ui.nav_sidebar import (
    HYDRAUMC_ECOSYSTEM_ITEMS,
    HYDRAUMC_ITEMS,
    INDUSTRIAL_ITEMS,
    ROOT_ITEMS,
    URTC_ITEMS,
)

# Real panels actually ported to Qt Quick content so far - every other key
# in the taxonomy above falls back to the honest "not yet migrated"
# placeholder (see NotMigratedPanel in Main.qml). Update this set as more
# real panels are ported; it is the ONE place that decides which content
# the QML content area shows for a given nav key.
MIGRATED_PANELS = frozenset({"logs", "overview", "servers", "robot", "trajectory", "ai_family", "admin_clients", "admin_logs", "admin_server", "ecosystem_services", "ecosystem_telemetry", "xy_table"})
_ADMIN_CLIENTS_POLL_MS = 5000
_ADMIN_LOGS_POLL_MS = 3000
_ADMIN_LOGS_LINES = 300

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _with_alpha(hex_color: str, alpha: float) -> str:
    """'#4caf50' + 0.13 -> 'rgba(76,175,80,0.13)' - QML's own color
    parsing accepts CSS rgba() strings directly, unlike the classic
    panel's own Qt style sheet hex-plus-alpha-suffix trick
    (f"{color}22"), which is a QSS-only convention this Qt Quick deck
    doesn't use anywhere else."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


@dataclass(frozen=True)
class _LogEntry:
    level: str
    logger_name: str
    message: str


class SuiteQtBridge(QObject):
    """Thin, UI-only bridge - real domain state stays on SuiteController
    (exposed to QML separately, unchanged, as context property
    'controller'). This class only owns things with no meaning outside a
    UI: which nav item is active, the ported panels' own QML-shaped
    display state, and i18n passthrough - the exact same division of
    responsibility URTC-TESTER/URTC-FLASHER's own bridges already use
    (their Property/Slot layer over an unmodified real backend)."""

    changed = Signal()
    _logsChanged = Signal()
    _trajectoryChanged = Signal()

    def __init__(self, controller: SuiteController) -> None:
        super().__init__()
        self._controller = controller
        self._active_key = "overview"
        self._connection_status = "disconnected"

        # -- Logs (ported from logs_panel.py's own LogsPanel - same real
        # algorithmic shape: an unbounded _all_entries plus a
        # currently-matching-filter _displayed_entries, both appended to
        # in O(1) per new record; only a filter change re-derives
        # _displayed_entries from _all_entries in one O(n) pass, exactly
        # matching that file's own _refresh_display). The QML-facing
        # Property caps to the most recent 500 for render performance
        # (a ListView with the full unbounded history would be slow to
        # lay out) - the one real, deliberate deviation from the
        # classic view's QTextEdit, which had no such cap.
        self._log_level_filter: str | None = None
        self._log_search_filter = ""
        self._all_log_entries: list[_LogEntry] = []
        self._displayed_log_entries: list[_LogEntry] = []
        handler = logging_handler.install()
        handler.emitter.record_logged.connect(self._on_log_record)

        # -- Overview (ported from overview.py's own OverviewPanel) --
        self._overview_name = "-"
        self._overview_ip = "-"
        self._overview_robot_count = "-"
        self._overview_online_count = "-"
        self._overview_cpu = "-"
        self._overview_mem = "-"
        self._overview_temp = "-"
        self._overview_uptime = "-"
        self._overview_robots: list[dict[str, object]] = []
        controller.active_state_changed.connect(self._on_overview_state_changed)
        controller.active_metrics_changed.connect(self._on_overview_metrics_changed)
        controller.active_status_changed.connect(self._on_connection_status)

        # -- Servers (ported from server_browser.py's own ServerBrowserPanel -
        # STATUS_DISPLAY_KEYS is imported from there directly rather than
        # copied, so both UIs always agree on the same real status wording). --
        self._server_statuses: dict[str, str] = {}
        self._server_login: dict[str, tuple[bool, str]] = {}
        self._scanning = False
        self._scan_status_text = ""
        controller.connections_changed.connect(self._on_servers_changed)
        controller.active_connection_changed.connect(lambda _cid: self._on_servers_changed())
        controller.connection_status_changed.connect(self._on_server_status)
        controller.connection_login_changed.connect(self._on_server_login)

        # -- Robot Control (ported from robot_control.py's own
        # RobotControlPanel - RotaryKnob's own custom-painted dial is not
        # reproduced here, a Slider alone already sets the exact same
        # real value the classic panel's knob+slider pair redundantly
        # show, so nothing real is lost). --
        self._selected_robot_id: str | None = None
        self._active_robots_cache: list[RobotView] = []
        # Trajectory (ported from trajectory_panel.py's own TrajectoryPanel -
        # a real local-only point recorder, NOT yet HYDRA-UMC-STUDIO's own
        # WORKS/*.json format, same real scope note that file's own header
        # gives). Reset only when the SELECTED ROBOT ITSELF changes (see
        # _select_robot below), never on every swarm tick.
        self._trajectory_points: list[dict[str, object]] = []
        controller.active_state_changed.connect(self._on_robot_state_changed)

        # -- AI Family Status (ported from ai_family_status_panel.py's own
        # AiFamilyStatusPanel - AI_FAMILIES imported directly from there,
        # never duplicated). --
        self._ai_family_projects: list[dict] = []
        self._ai_family_ai_hailo: dict[str, str] = {}
        self._ai_family_status_text = _("LBL_ES_NOT_LOADED")
        self._ai_family_refreshing = False
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_ai_family()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_ai_family()))
        asyncio.ensure_future(self._refresh_ai_family())

        # -- Admin Clients (ported from admin_clients_panel.py's own
        # AdminClientsPanel - _relative_duration imported directly from
        # there, never duplicated). Real 5s data poll + a separate 1s
        # tick that only re-emits changed so the "Xm ago" durations
        # advance smoothly between polls, matching that file's own real
        # two-timer design exactly. --
        self._admin_clients: list[dict] = []
        self._admin_clients_status_text = _("MSG_ADMIN_ONLY")
        self._admin_clients_timer = QTimer(self)
        self._admin_clients_timer.setInterval(_ADMIN_CLIENTS_POLL_MS)
        self._admin_clients_timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh_admin_clients()))
        self._admin_clients_timer.start()
        self._admin_clients_tick_timer = QTimer(self)
        self._admin_clients_tick_timer.setInterval(1000)
        self._admin_clients_tick_timer.timeout.connect(self.changed.emit)
        self._admin_clients_tick_timer.start()
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_clients()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_clients()))
        asyncio.ensure_future(self._refresh_admin_clients())

        # -- Admin Logs (ported from admin_logs_panel.py's own
        # AdminLogsPanel - _extract_tag imported directly from there,
        # never duplicated). Same real "clear the screen, keep tailing"
        # anchor trick, live/pause, and tag+search filtering. --
        self._admin_logs_live = True
        self._admin_logs_all_lines: list[str] = []
        self._admin_logs_tag_filter: str | None = None
        self._admin_logs_search = ""
        self._admin_logs_cleared_anchor: str | None = None
        self._admin_logs_cleared_at_empty = False
        self._admin_logs_status_text = _("MSG_ADMIN_ONLY")
        self._admin_logs_timer = QTimer(self)
        self._admin_logs_timer.setInterval(_ADMIN_LOGS_POLL_MS)
        self._admin_logs_timer.timeout.connect(lambda: asyncio.ensure_future(self._refresh_admin_logs()))
        self._admin_logs_timer.start()
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_logs()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_logs()))
        asyncio.ensure_future(self._refresh_admin_logs())

        # -- Admin Server (ported from admin_server_panel.py's own
        # AdminServerPanel - _format_uptime imported directly from
        # there, never duplicated). --
        self._admin_server_status_text = _("MSG_ADMIN_ONLY")
        self._admin_server_current_port: int | None = None
        self._admin_server_pending_port_text = ""
        self._admin_server_info: dict[str, object] = {}
        controller.active_connection_changed.connect(lambda _cid: asyncio.ensure_future(self._refresh_admin_server()))
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: asyncio.ensure_future(self._refresh_admin_server()))
        asyncio.ensure_future(self._refresh_admin_server())

        # -- Ecosystem Services (ported from ecosystem_services_panel.py's
        # own EcosystemServicesPanel - _health/_badge_label/_HEALTH_COLOR/
        # _STACK_COLOR imported directly from there, never duplicated). --
        self._es_projects: list[dict] = []
        self._es_family_filter: str | None = None
        self._es_search = ""
        self._es_actioning_unit: str | None = None
        self._es_action_error: tuple[str, str] | None = None
        self._es_status_text = _("LBL_ES_NOT_LOADED")
        self._es_refreshing = False
        controller.connection_login_changed.connect(lambda _cid, _ok, _detail: self.changed.emit())

        # -- Ecosystem Telemetry (ported from ecosystem_telemetry_panel.py's
        # own EcosystemTelemetryPanel - _AGGREGATES/_RANGE_PRESETS imported
        # directly from there, never duplicated). Real chart rendering
        # uses a hand-drawn QML Canvas, NOT `import QtCharts` in QML -
        # that module segfaults on load in this real environment (PySide6
        # 6.11.1, confirmed both offscreen and on-screen) - see this
        # session's own memory note. --
        self._tel_status_text = ""
        self._tel_running = False
        self._tel_is_aggregate = False
        self._tel_chart_mode = "empty"
        self._tel_line_points: list[dict[str, float]] = []
        self._tel_bars: list[dict[str, object]] = []
        self._tel_stats: dict[str, str] = {}

        # -- XY Table (ported from xy_table_panel.py's own XYTablePanel -
        # _default_xy_table/_DISPLAY_DEFAULT_SIZE_MM/JOG_STEPS_MM
        # imported directly from there, never duplicated. Own real,
        # independent robot selection - NOT shared with Robot Control/
        # Trajectory's own, matching the classic panel's own real
        # independent QComboBox). --
        self._xy_selected_robot_id: str | None = None
        self._xy_jog_step_mm = 10.0
        self._xy_robots_cache: list[RobotView] = []
        controller.active_state_changed.connect(self._on_xy_state_changed)

    # -- navigation --------------------------------------------------------

    @Property(str, notify=changed)
    def activePanel(self) -> str:
        return self._active_key

    @Property(bool, notify=changed)
    def activePanelMigrated(self) -> bool:
        return self._active_key in MIGRATED_PANELS

    @Slot(str)
    def navigatePanel(self, key: str) -> None:
        if key != self._active_key:
            self._active_key = key
            self.changed.emit()

    @Property("QVariantList", constant=True)
    def rootItems(self) -> list[dict[str, str]]:
        return self._items(ROOT_ITEMS)

    @Property("QVariantList", constant=True)
    def industrialItems(self) -> list[dict[str, str]]:
        return self._items(INDUSTRIAL_ITEMS)

    @Property("QVariantList", constant=True)
    def urtcItems(self) -> list[dict[str, str]]:
        return self._items(URTC_ITEMS)

    @Property("QVariantList", constant=True)
    def hydraumcItems(self) -> list[dict[str, str]]:
        return self._items(HYDRAUMC_ITEMS)

    @Property("QVariantList", constant=True)
    def hydraumcEcosystemItems(self) -> list[dict[str, str]]:
        return self._items(HYDRAUMC_ECOSYSTEM_ITEMS)

    @staticmethod
    def _items(pairs: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
        return [{"label": _(label_key), "key": key, "migrated": key in MIGRATED_PANELS} for label_key, key in pairs]

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def iconSource(self) -> str:
        svg = IMAGES_DIR / "HYDRA_UMC_ICON.svg"
        return QUrl.fromLocalFile(str(svg)).toString() if svg.is_file() else ""

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        translated = _(key)
        return translated if translated != key else key

    @Property(str, notify=changed)
    def connectionStatus(self) -> str:
        return self._connection_status

    @Slot(str)
    def _on_connection_status(self, status: str) -> None:
        self._connection_status = status
        self.changed.emit()

    # -- Logs ----------------------------------------------------------

    def _entry_matches_filters(self, entry: _LogEntry) -> bool:
        if self._log_level_filter is not None and entry.level != self._log_level_filter:
            return False
        needle = self._log_search_filter.strip().lower()
        if needle and needle not in entry.message.lower() and needle not in entry.logger_name.lower():
            return False
        return True

    def _on_log_record(self, level: str, logger_name: str, message: str) -> None:
        entry = _LogEntry(level, logger_name, message)
        self._all_log_entries.append(entry)
        if self._entry_matches_filters(entry):
            self._displayed_log_entries.append(entry)
            self._logsChanged.emit()

    @Property("QVariantList", notify=_logsChanged)
    def logEntries(self) -> list[dict[str, str]]:
        return [
            {"level": e.level, "logger": e.logger_name, "message": e.message}
            for e in self._displayed_log_entries[-500:]
        ]

    @Property("QStringList", constant=True)
    def logLevels(self) -> list[str]:
        return [_("LOG_LEVEL_ALL"), *_LOG_LEVELS]

    @Slot(str)
    def setLogLevelFilter(self, level: str) -> None:
        wanted = None if level == _("LOG_LEVEL_ALL") else level
        if wanted != self._log_level_filter:
            self._log_level_filter = wanted
            self._refresh_log_display()

    @Slot(str)
    def setLogSearchFilter(self, text: str) -> None:
        if text != self._log_search_filter:
            self._log_search_filter = text
            self._refresh_log_display()

    def _refresh_log_display(self) -> None:
        self._displayed_log_entries = [e for e in self._all_log_entries if self._entry_matches_filters(e)]
        self._logsChanged.emit()

    @Slot()
    def clearLogs(self) -> None:
        self._all_log_entries.clear()
        self._displayed_log_entries.clear()
        self._logsChanged.emit()

    # -- Servers ---------------------------------------------------------

    @Property("QVariantList", notify=changed)
    def serverRows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        active_id = self._controller._active_id  # same real field server_browser.py's own _refresh_table reads directly
        for conn_id, conn in self._controller.connections.items():
            robot_count = len(conn.state.active_controller.robots) if conn.state.active_controller else conn.info.robot_count
            login = self._server_login.get(conn_id)
            if login is not None and not login[0]:
                status_key = "login_failed"
            else:
                status_key = self._server_statuses.get(conn_id, "connecting")
            rows.append({
                "connId": conn_id,
                "name": conn.info.display_name,
                "hostPort": f"{conn.info.host}:{conn.info.port}",
                "robotCount": robot_count,
                "statusText": _(STATUS_DISPLAY_KEYS.get(status_key, "STATUS_CONNECTING")),
                "loginDetail": login[1] if login is not None and not login[0] else "",
                "active": conn_id == active_id,
            })
        return rows

    @Property(bool, notify=changed)
    def serverScanning(self) -> bool:
        return self._scanning

    @Property(str, notify=changed)
    def serverScanStatus(self) -> str:
        return self._scan_status_text

    @Property(int, constant=True)
    def defaultServerPort(self) -> int:
        return DEFAULT_PORT

    def _on_servers_changed(self) -> None:
        self.changed.emit()

    def _on_server_status(self, conn_id: str, status: str) -> None:
        self._server_statuses[conn_id] = status
        self.changed.emit()

    def _on_server_login(self, conn_id: str, ok: bool, detail: str) -> None:
        self._server_login[conn_id] = (ok, detail)
        self.changed.emit()

    @Slot()
    def scanServers(self) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._scan_status_text = _("STATUS_SCANNING")
        self.changed.emit()
        asyncio.ensure_future(self._run_server_scan())

    async def _run_server_scan(self) -> None:
        # discover_servers() runs the brute-force subnet scan and real
        # mDNS/Bonjour discovery CONCURRENTLY (net/discovery.py's own
        # header comment) and dedupes between them - same real call
        # server_browser.py's own _run_scan makes, unchanged.
        found = 0
        try:
            async for info in discover_servers():
                found += 1
                self._controller.add_server(info)
                self._scan_status_text = _("STATUS_SCANNING_PROGRESS", found=found)
                self.changed.emit()
        finally:
            self._scanning = False
            self._scan_status_text = _("STATUS_SCAN_COMPLETE", found=found) if found else _("STATUS_SCAN_COMPLETE_NONE")
            self.changed.emit()

    @Slot(str, int, str, str)
    def addManualServer(self, host: str, port: int, username: str, password: str) -> None:
        host = host.strip()
        username = username.strip()
        if not host or not username or not password:
            return
        info = ServerInfo(host=host, port=port, hostname=host, username=username, password=password)
        self._controller.add_server(info)

    @Slot(str)
    def setActiveServer(self, conn_id: str) -> None:
        self._controller.set_active(conn_id)

    @Slot(str)
    def removeServer(self, conn_id: str) -> None:
        self._controller.remove_server(conn_id)

    @Slot(str, result="QVariant")
    def serverCredentials(self, conn_id: str) -> dict[str, str]:
        conn = self._controller.connections.get(conn_id)
        if conn is None:
            return {"username": "", "password": ""}
        return {"username": conn.info.username, "password": conn.info.password}

    @Slot(str, str, str)
    def saveServerCredentials(self, conn_id: str, username: str, password: str) -> None:
        conn = self._controller.connections.get(conn_id)
        if conn is None or not username or not password:
            return
        conn.info.username = username
        conn.info.password = password
        # Credentials just changed - force a clean reconnect rather than
        # waiting for HydraConnection's own retry loop to notice on its
        # own timer, same real reason server_browser.py's own
        # _on_edit_credentials does this.
        asyncio.ensure_future(self._reconnect_server(conn))

    @staticmethod
    async def _reconnect_server(conn) -> None:
        await conn.disconnect()
        await conn.connect()

    # -- Robot Control -----------------------------------------------------

    def _active_robots(self) -> list[RobotView]:
        # Cached from the last real active_state_changed delivery (see
        # _on_robot_state_changed below) rather than re-derived from
        # self._controller.active_state on every call - matches
        # robot_control.py's own real pattern (it caches
        # self._current_robot from the state PARAMETER a signal handler
        # receives, never re-queries the controller independently
        # elsewhere), and avoids a real staleness risk: re-deriving here
        # would only coincidentally agree with what the signal just
        # carried.
        return self._active_robots_cache

    def _selected_robot(self) -> RobotView | None:
        for r in self._active_robots():
            if r.id == self._selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=changed)
    def robotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.id} — {r.model}"} for r in self._active_robots()]

    @Property(str, notify=changed)
    def selectedRobotId(self) -> str:
        return self._selected_robot_id or ""

    @Property(bool, notify=changed)
    def canControlRobot(self) -> bool:
        return self._selected_robot() is not None

    @Property(str, notify=changed)
    def selectedRobotLabel(self) -> str:
        robot = self._selected_robot()
        return _("LBL_ROBOT_SELECTED", id=robot.id, model=robot.model) if robot is not None else _("LBL_NO_ROBOT_SELECTED")

    @Property("QVariantList", notify=changed)
    def selectedRobotJoints(self) -> list[dict[str, object]]:
        robot = self._selected_robot()
        joints = robot.joints if robot is not None else {}
        return [{"name": name, "value": joints.get(name, 0.0)} for name in JOINT_NAMES]

    @Property(int, notify=changed)
    def selectedRobotSpeed(self) -> int:
        robot = self._selected_robot()
        return int(robot.speed) if robot is not None else 100

    @Property(int, notify=changed)
    def selectedRobotAcceleration(self) -> int:
        robot = self._selected_robot()
        return int(robot.acceleration) if robot is not None else 100

    def _on_robot_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        self._active_robots_cache = robots
        if self._selected_robot_id not in {r.id for r in robots}:
            self._select_robot(robots[0].id if robots else None)
        self.changed.emit()

    @Slot(str)
    def selectRobot(self, robot_id: str) -> None:
        self._select_robot(robot_id or None)
        self.changed.emit()

    def _select_robot(self, new_id: str | None) -> None:
        """The one real place _selected_robot_id ever changes - resets
        the recorded trajectory points exactly like
        trajectory_panel.py's own set_selected_robot does (only on an
        actual robot-identity change, never on every swarm tick a
        continuing selection would otherwise wipe recordings within
        moments of making them)."""
        if new_id == self._selected_robot_id:
            return
        self._selected_robot_id = new_id
        self._trajectory_points = []
        self._trajectoryChanged.emit()

    @Slot(str, float)
    def setJoint(self, joint_name: str, value: float) -> None:
        robot = self._selected_robot()
        if robot is None or joint_name not in JOINT_NAMES:
            return
        new_joints = dict(robot.joints)
        new_joints[joint_name] = value

        def local_mutate(r: RobotView, joints=new_joints) -> None:
            for name, joint_value in joints.items():
                r.set_joint(name, joint_value)

        # Same real atomic 'jog' command + 50ms debounce as
        # robot_control.py's own _on_joint_changed - see that method's
        # own comment for why a full 6-joint override, debounced, is
        # safe here.
        self._controller.send_robot_command(
            robot.id, "jog",
            {"axis": "x", "amount": 0, "target": "robot", "joints": new_joints},
            local_mutate,
            debounce_ms=50,
        )
        self.changed.emit()

    @Slot(int)
    def setRobotSpeed(self, value: int) -> None:
        robot = self._selected_robot()
        if robot is None:
            return
        self._controller.send_robot_command(
            robot.id, "speed", {"speed": value}, lambda r, v=value: r.set_speed(v), debounce_ms=300
        )
        self.changed.emit()

    @Slot(int)
    def setRobotAcceleration(self, value: int) -> None:
        robot = self._selected_robot()
        if robot is None:
            return
        self._controller.send_robot_command(
            robot.id, "speed", {"acceleration": value}, lambda r, v=value: r.set_acceleration(v), debounce_ms=300
        )
        self.changed.emit()

    # -- Trajectory --------------------------------------------------------

    @Property("QVariantList", notify=_trajectoryChanged)
    def trajectoryPoints(self) -> list[dict[str, object]]:
        return [
            {"time": p["_time"], "joints": " / ".join(f"{p[name]:.1f}" for name in JOINT_NAMES)}
            for p in self._trajectory_points
        ]

    @Slot()
    def recordTrajectoryPoint(self) -> None:
        robot = self._selected_robot()
        if robot is None:
            return
        point: dict[str, object] = dict(robot.joints)
        point["_time"] = time.strftime("%H:%M:%S")
        self._trajectory_points.append(point)
        self._trajectoryChanged.emit()

    @Slot(int)
    def applyTrajectoryPoint(self, index: int) -> None:
        robot = self._selected_robot()
        if robot is None or not 0 <= index < len(self._trajectory_points):
            return
        point = self._trajectory_points[index]
        for name in JOINT_NAMES:
            robot.set_joint(name, point[name])
        self._controller.push_active_state()

    @Slot(int)
    def deleteTrajectoryPoint(self, index: int) -> None:
        if 0 <= index < len(self._trajectory_points):
            del self._trajectory_points[index]
            self._trajectoryChanged.emit()

    # -- AI Family Status --------------------------------------------------

    @Property(str, notify=changed)
    def aiFamilyStatusText(self) -> str:
        return self._ai_family_status_text

    @Property(bool, notify=changed)
    def aiFamilyRefreshing(self) -> bool:
        return self._ai_family_refreshing

    @Property("QVariantList", notify=changed)
    def aiFamilyGroups(self) -> list[dict[str, object]]:
        groups: list[dict[str, object]] = []
        for family, device_key, device_label in AI_FAMILIES:
            items = [p for p in self._ai_family_projects if p.get("family") == family]
            live_count = sum(1 for p in items if p.get("live") is True)
            configured = self._ai_family_ai_hailo.get("visionDevice" if device_key == "hailo8" else "cognitiveDevice", "none")
            title = _("LBL_AI_FAMILY_VISION", device=device_label) if device_key == "hailo8" else _("LBL_AI_FAMILY_COGNITIVE", device=device_label)
            groups.append({
                "title": title,
                "devicePill": _("LBL_NONE_DEVICE") if configured == "none" else device_label,
                "deviceConfigured": configured != "none",
                "countText": _("LBL_AI_FAMILY_LIVE_COUNT", live=live_count, total=len(items)),
                "mismatchWarning": _("MSG_AI_FAMILY_DEVICE_MISMATCH", family=family, device=device_label) if live_count > 0 and configured == "none" else "",
                "projects": [
                    {
                        "name": str(p.get("name") or "-"),
                        "meta": f"{p.get('role') or '-'} · v{p.get('version') or '-'}",
                        "statusText": _("STATUS_ES_LIVE") if p.get("live") is True else (_("STATUS_ES_DEAD") if p.get("live") is False else _("STATUS_ES_NA")),
                        "live": p.get("live"),
                    }
                    for p in items
                ],
            })
        return groups

    @Slot()
    def refreshAiFamily(self) -> None:
        asyncio.ensure_future(self._refresh_ai_family())

    async def _refresh_ai_family(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._ai_family_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        self._ai_family_refreshing = True
        self.changed.emit()
        try:
            result = await conn.fetch_ecosystem_status()
        finally:
            self._ai_family_refreshing = False
        if result is None:
            self._ai_family_status_text = _("MSG_ES_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict) or not body.get("available"):
            self._ai_family_status_text = _("MSG_ES_UNAVAILABLE")
            self.changed.emit()
            return
        self._ai_family_status_text = ""
        families = {f for f, _dev, _label in AI_FAMILIES}
        self._ai_family_projects = [p for p in (body.get("projects") or []) if p.get("family") in families]
        self._ai_family_ai_hailo = conn.state.ai_hailo
        self.changed.emit()

    # -- Admin Clients -----------------------------------------------------

    @Property(str, notify=changed)
    def adminClientsStatusText(self) -> str:
        return self._admin_clients_status_text

    @Property(bool, notify=changed)
    def adminClientsShowStats(self) -> bool:
        return len(self._admin_clients) > 0

    @Property(int, notify=changed)
    def adminClientsConnectedCount(self) -> int:
        return len(self._admin_clients)

    @Property(int, notify=changed)
    def adminClientsAdminCount(self) -> int:
        return sum(1 for c in self._admin_clients if c.get("role") == "admin")

    @Property("QVariantList", notify=changed)
    def adminClientsRows(self) -> list[dict[str, object]]:
        sorted_clients = sorted(
            self._admin_clients,
            key=lambda c: (c.get("role") != "admin", str(c.get("username") or "")),
        )
        return [
            {
                "username": str(c.get("username") or _("LBL_CLIENT_UNKNOWN")),
                "address": str(c.get("remoteAddress") or "-"),
                "isAdmin": c.get("role") == "admin",
                "roleLabel": str(c.get("role") or "?").upper(),
                "duration": _relative_duration(c.get("connectedAt")),
                "connected": bool(c.get("connected")),
            }
            for c in sorted_clients
        ]

    async def _refresh_admin_clients(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._admin_clients_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self._admin_clients = []
            self.changed.emit()
            return
        if not conn.is_admin:
            self._admin_clients_status_text = _("MSG_ADMIN_ONLY")
            self._admin_clients = []
            self.changed.emit()
            return
        result = await conn.fetch_admin_clients()
        if result is None:
            self._admin_clients_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._admin_clients_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_clients = body.get("clients") or []
        self._admin_clients_status_text = _("LBL_CLIENTS_REFRESH_NOTE", seconds=_ADMIN_CLIENTS_POLL_MS // 1000)
        self.changed.emit()

    # -- Admin Logs --------------------------------------------------------

    @Property(str, notify=changed)
    def adminLogsStatusText(self) -> str:
        return self._admin_logs_status_text

    @Property(bool, notify=changed)
    def adminLogsLive(self) -> bool:
        return self._admin_logs_live

    @Property(str, notify=changed)
    def adminLogsTagFilter(self) -> str:
        return self._admin_logs_tag_filter or ""

    @Property("QStringList", notify=changed)
    def adminLogsTags(self) -> list[str]:
        return sorted({tag for line in self._admin_logs_all_lines if (tag := _extract_tag(line))})

    def _admin_logs_displayed_lines(self) -> list[str]:
        if not self._admin_logs_cleared_at_empty and self._admin_logs_cleared_anchor is None:
            return self._admin_logs_all_lines
        if self._admin_logs_cleared_at_empty:
            return self._admin_logs_all_lines
        try:
            idx = len(self._admin_logs_all_lines) - 1 - self._admin_logs_all_lines[::-1].index(self._admin_logs_cleared_anchor)
        except ValueError:
            # Anchor scrolled off the server's own LINES-line window - show
            # everything rather than hide real content, same real reason
            # admin_logs_panel.py's own _displayed_lines does.
            return self._admin_logs_all_lines
        return self._admin_logs_all_lines[idx + 1:]

    @Property("QStringList", notify=changed)
    def adminLogsLines(self) -> list[str]:
        displayed = self._admin_logs_displayed_lines()
        needle = self._admin_logs_search.strip().lower()
        filtered = [
            line for line in displayed
            if (self._admin_logs_tag_filter is None or _extract_tag(line) == self._admin_logs_tag_filter)
            and (not needle or needle in line.lower())
        ]
        if not filtered:
            return [_("MSG_LOGS_NONE") if not displayed else _("LOGS_NO_MATCH")]
        return filtered

    @Slot()
    def toggleAdminLogsLive(self) -> None:
        self._admin_logs_live = not self._admin_logs_live
        self.changed.emit()

    @Slot()
    def clearAdminLogs(self) -> None:
        if self._admin_logs_all_lines:
            self._admin_logs_cleared_anchor = self._admin_logs_all_lines[-1]
            self._admin_logs_cleared_at_empty = False
        else:
            self._admin_logs_cleared_anchor = None
            self._admin_logs_cleared_at_empty = True
        self.changed.emit()

    @Slot(str)
    def setAdminLogsTagFilter(self, tag: str) -> None:
        self._admin_logs_tag_filter = tag or None
        self.changed.emit()

    @Slot(str)
    def setAdminLogsSearch(self, text: str) -> None:
        self._admin_logs_search = text
        self.changed.emit()

    async def _refresh_admin_logs(self) -> None:
        if not self._admin_logs_live:
            return
        conn = self._controller.active_connection
        if conn is None:
            self._admin_logs_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        if not conn.is_admin:
            self._admin_logs_status_text = _("MSG_ADMIN_ONLY")
            self._admin_logs_all_lines = []
            self.changed.emit()
            return
        result = await conn.fetch_admin_logs(_ADMIN_LOGS_LINES)
        if result is None:
            self._admin_logs_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._admin_logs_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_logs_all_lines = body.get("lines") or []
        self._admin_logs_status_text = _("LBL_LOGS_FOOTER_LIVE", lines=_ADMIN_LOGS_LINES, seconds=_ADMIN_LOGS_POLL_MS // 1000)
        self.changed.emit()

    # -- Admin Server ------------------------------------------------------

    @Property(str, notify=changed)
    def adminServerStatusText(self) -> str:
        return self._admin_server_status_text

    @Property(bool, notify=changed)
    def adminServerInfoVisible(self) -> bool:
        return bool(self._admin_server_info)

    @Property(str, notify=changed)
    def adminServerProduct(self) -> str:
        return str(self._admin_server_info.get("product") or "-")

    @Property(str, notify=changed)
    def adminServerVersion(self) -> str:
        version = self._admin_server_info.get("appVersion")
        return f"v{version}" if version else "-"

    @Property(str, notify=changed)
    def adminServerUptime(self) -> str:
        return _format_uptime(self._admin_server_info.get("uptimeSeconds"))

    @Property(str, notify=changed)
    def adminServerControllerCount(self) -> str:
        return str(self._admin_server_info.get("controllerCount", "-"))

    @Property(str, notify=changed)
    def adminServerRobotCount(self) -> str:
        return str(self._admin_server_info.get("robotCount", "-"))

    @Property(str, notify=changed)
    def adminServerHost(self) -> str:
        return str(self._admin_server_info.get("hostname") or "-")

    @Property(str, notify=changed)
    def adminServerPortLabel(self) -> str:
        port = self._admin_server_current_port if self._admin_server_current_port is not None else "..."
        return _("LBL_ADMIN_SERVER_PORT_CURRENT", port=port)

    @Property(str, notify=changed)
    def adminServerPendingPortText(self) -> str:
        return self._admin_server_pending_port_text

    async def _refresh_admin_server(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._admin_server_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        if not conn.is_admin:
            self._admin_server_status_text = _("MSG_ADMIN_ONLY")
            self.changed.emit()
            return
        result = await conn.fetch_admin_server_config()
        if result is None:
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_server_status_text = ""
        self._admin_server_current_port = body.get("port")
        pending = body.get("pendingPort")
        self._admin_server_pending_port_text = str(pending if pending is not None else self._admin_server_current_port or "")

        info_result = await conn.fetch_hydra_info()
        if info_result is not None:
            info_status, info_body = info_result
            if info_status == 200 and isinstance(info_body, dict):
                self._admin_server_info = info_body
        self.changed.emit()

    @Slot(str)
    def saveAdminServerPort(self, text: str) -> None:
        asyncio.ensure_future(self._save_admin_server_port(text))

    async def _save_admin_server_port(self, text: str) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        try:
            port = int(text)
        except ValueError:
            self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_INVALID")
            self.changed.emit()
            return
        if not (1 <= port <= 65535):
            self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_INVALID")
            self.changed.emit()
            return
        result = await conn.save_admin_server_port(port)
        if result is None or result[0] != 200:
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_server_status_text = _("MSG_ADMIN_SERVER_PORT_SAVED")
        self.changed.emit()

    @Slot()
    def restartAdminServer(self) -> None:
        asyncio.ensure_future(self._restart_admin_server())

    async def _restart_admin_server(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        result = await conn.restart_server()
        if result is None or result[0] != 200:
            self._admin_server_status_text = _("MSG_ADMIN_LOAD_ERROR")
            self.changed.emit()
            return
        self._admin_server_status_text = _("MSG_ADMIN_SERVER_RESTART_REQUESTED")
        self.changed.emit()

    # -- Ecosystem Services --------------------------------------------------

    @Property(str, notify=changed)
    def esStatusText(self) -> str:
        return self._es_status_text

    @Property(bool, notify=changed)
    def esRefreshing(self) -> bool:
        return self._es_refreshing

    @Property(str, notify=changed)
    def esFamilyFilter(self) -> str:
        return self._es_family_filter or ""

    @Property("QStringList", notify=changed)
    def esFamilies(self) -> list[str]:
        return sorted({p.get("family") for p in self._es_projects if p.get("family")})

    @Property(bool, notify=changed)
    def esShowStats(self) -> bool:
        return len(self._es_projects) > 0

    @Property("QVariantMap", notify=changed)
    def esStats(self) -> dict[str, int]:
        return {
            "total": len(self._es_projects),
            "live": sum(1 for p in self._es_projects if p.get("live") is True),
            "families": len({p.get("family") for p in self._es_projects if p.get("family")}),
            "running": sum(1 for p in self._es_projects if _health(p) == "green"),
            "stopped": sum(1 for p in self._es_projects if _health(p) == "red"),
            "error": sum(1 for p in self._es_projects if _health(p) == "amber"),
            "na": sum(1 for p in self._es_projects if _health(p) == "slate"),
        }

    @Property("QVariantList", notify=changed)
    def esGroups(self) -> list[dict[str, object]]:
        needle = self._es_search.strip().lower()
        filtered = [
            p for p in self._es_projects
            if (self._es_family_filter is None or p.get("family") == self._es_family_filter)
            and (not needle or needle in str(p.get("name", "")).lower())
        ]
        grouped: dict[str, list[dict]] = {}
        for p in filtered:
            key = p.get("family") or _("SERVICES_NO_FAMILY")
            grouped.setdefault(key, []).append(p)

        conn = self._controller.active_connection
        is_admin = conn is not None and conn.is_admin
        groups = []
        for family in sorted(grouped.keys()):
            items = grouped[family]
            cards = []
            for p in items:
                health = _health(p)
                unit = p.get("systemdUnit")
                error = self._es_action_error if self._es_action_error is not None and self._es_action_error[0] == unit else None
                health_color = _HEALTH_COLOR[health]
                cards.append({
                    "name": str(p.get("name") or "-"),
                    "badgeText": _badge_label(p),
                    "healthColor": health_color,
                    "healthColorBg": _with_alpha(health_color, 0.13),
                    "healthColorBorder": _with_alpha(health_color, 0.33),
                    "version": f"v{p.get('version')}" if p.get("version") else "",
                    "stack": p.get("stack") or "",
                    "stackColor": _STACK_COLOR.get(p.get("stack"), "#7f8ea1"),
                    "maturity": p.get("maturity") or "",
                    "hostPort": f"{p.get('serviceHost')}:{p.get('servicePort')}" if p.get("serviceHost") else "",
                    "pidText": f"{_('LBL_SERVICES_PID')} {p.get('pid')}" if p.get("pid") is not None else "",
                    "canControl": bool(is_admin and unit),
                    "unit": unit or "",
                    "actioning": self._es_actioning_unit == unit,
                    "errorText": error[1] if error is not None else "",
                })
            groups.append({"family": family, "count": len(items), "cards": cards})
        return groups

    @Slot()
    def refreshEcosystemServices(self) -> None:
        asyncio.ensure_future(self._refresh_ecosystem_services())

    async def _refresh_ecosystem_services(self) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._es_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        self._es_refreshing = True
        self.changed.emit()
        try:
            result = await conn.fetch_ecosystem_status()
        finally:
            self._es_refreshing = False
        if result is None:
            self._es_status_text = _("MSG_ES_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status != 200 or not isinstance(body, dict):
            self._es_status_text = _("MSG_ES_LOAD_ERROR")
            self.changed.emit()
            return
        if not body.get("available"):
            self._es_status_text = _("MSG_ES_UNAVAILABLE")
            self._es_projects = []
            self.changed.emit()
            return
        self._es_projects = body.get("projects") or []
        self._es_status_text = _("LBL_ES_SCANNED_AT", time=body.get("scannedAt") or "-")
        self.changed.emit()

    @Slot(str)
    def setEsFamilyFilter(self, family: str) -> None:
        self._es_family_filter = family or None
        self.changed.emit()

    @Slot(str)
    def setEsSearch(self, text: str) -> None:
        self._es_search = text
        self.changed.emit()

    @Slot(str, str)
    def runEsServiceAction(self, unit: str, action: str) -> None:
        asyncio.ensure_future(self._run_es_service_action(unit, action))

    async def _run_es_service_action(self, unit: str, action: str) -> None:
        conn = self._controller.active_connection
        if conn is None:
            return
        self._es_actioning_unit = unit
        self._es_action_error = None
        self.changed.emit()
        try:
            result = await conn.control_service(unit, action)
        finally:
            self._es_actioning_unit = None
        if result is None:
            self._es_action_error = (unit, _("MSG_SERVICES_ACTION_ERROR"))
            self.changed.emit()
            return
        status, body = result
        if status != 200:
            message = body.get("error") if isinstance(body, dict) else None
            self._es_action_error = (unit, message or f"HTTP {status}")
            self.changed.emit()
            return
        await self._refresh_ecosystem_services()

    # -- Ecosystem Telemetry -------------------------------------------------

    @Property(str, notify=changed)
    def telemetryStatusText(self) -> str:
        return self._tel_status_text

    @Property(bool, notify=changed)
    def telemetryRunning(self) -> bool:
        return self._tel_running

    @Property("QStringList", constant=True)
    def telemetryAggregates(self) -> list[str]:
        return list(_AGGREGATES)

    @Property("QVariantList", constant=True)
    def telemetryRangePresets(self) -> list[dict[str, object]]:
        return [{"label": label, "ms": ms} for label, ms in _RANGE_PRESETS]

    @Property(bool, notify=changed)
    def telemetryShowStats(self) -> bool:
        return bool(self._tel_stats)

    @Property("QVariantMap", notify=changed)
    def telemetryStats(self) -> dict[str, str]:
        return self._tel_stats

    @Property(str, notify=changed)
    def telemetryChartMode(self) -> str:
        return self._tel_chart_mode

    @Property("QVariantList", notify=changed)
    def telemetryLinePoints(self) -> list[dict[str, float]]:
        return self._tel_line_points

    @Property("QVariantList", notify=changed)
    def telemetryBars(self) -> list[dict[str, object]]:
        return self._tel_bars

    @Slot(str, str, str, str, str, str, str, str)
    def runTelemetryQuery(
        self, mode: str, source_id: str, kind: str, field: str,
        start: str, end: str, bucket_ms: str, agg: str,
    ) -> None:
        asyncio.ensure_future(self._run_telemetry_query(mode, source_id, kind, field, start, end, bucket_ms, agg))

    async def _run_telemetry_query(
        self, mode: str, source_id: str, kind: str, field: str,
        start: str, end: str, bucket_ms: str, agg: str,
    ) -> None:
        conn = self._controller.active_connection
        if conn is None:
            self._tel_status_text = _("LBL_ES_NO_ACTIVE_SERVER")
            self.changed.emit()
            return
        is_aggregate = mode == "aggregate"
        params: dict[str, str] = {}
        if source_id:
            params["sourceId"] = source_id
        if kind:
            params["kind"] = kind
        if field:
            params["field"] = field
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        self._tel_running = True
        self.changed.emit()
        try:
            if is_aggregate:
                if not (kind and field and start and end):
                    self._tel_status_text = _("MSG_TELEMETRY_AGGREGATE_MISSING_FIELDS")
                    return
                params["bucketMs"] = bucket_ms
                params["agg"] = agg
                result = await conn.fetch_telemetry_aggregate(params)
            else:
                result = await conn.fetch_telemetry_query(params)
        finally:
            self._tel_running = False
            self.changed.emit()

        if result is None:
            self._tel_status_text = _("MSG_TELEMETRY_LOAD_ERROR")
            self.changed.emit()
            return
        status, body = result
        if status == 503 and isinstance(body, dict) and body.get("available") is False:
            self._tel_status_text = _("MSG_TELEMETRY_NOT_CONFIGURED")
            self._render_empty_telemetry_chart()
            self._update_telemetry_stats([])
            self.changed.emit()
            return
        if status != 200 or not isinstance(body, list):
            self._tel_status_text = _("MSG_TELEMETRY_LOAD_ERROR")
            self.changed.emit()
            return

        self._tel_status_text = "" if body else _("MSG_TELEMETRY_NO_DATA")
        if is_aggregate:
            self._render_telemetry_bar_chart(body)
            self._update_telemetry_stats([float(b.get("value", 0)) for b in body])
        else:
            self._render_telemetry_line_chart(body)
            self._update_telemetry_stats([float(p.get("value", 0)) for p in body])
        self.changed.emit()

    def _render_empty_telemetry_chart(self) -> None:
        self._tel_chart_mode = "empty"
        self._tel_line_points = []
        self._tel_bars = []

    def _render_telemetry_line_chart(self, points: list[dict]) -> None:
        if not points:
            self._render_empty_telemetry_chart()
            return
        self._tel_chart_mode = "line"
        self._tel_bars = []
        timestamps = [float(p.get("timestamp", 0)) for p in points]
        values = [float(p.get("value", 0)) for p in points]
        t_min, t_max = min(timestamps), max(timestamps)
        v_min, v_max = min(values), max(values)
        t_span = (t_max - t_min) or 1.0
        v_span = (v_max - v_min) or 1.0
        self._tel_line_points = [
            {
                "nx": (t - t_min) / t_span,
                "ny": (v - v_min) / v_span if v_max != v_min else 0.5,
            }
            for t, v in zip(timestamps, values)
        ]

    def _render_telemetry_bar_chart(self, buckets: list[dict]) -> None:
        if not buckets:
            self._render_empty_telemetry_chart()
            return
        self._tel_chart_mode = "bar"
        self._tel_line_points = []
        values = [float(b.get("value", 0)) for b in buckets]
        v_max = max(values) or 1.0
        self._tel_bars = [
            {
                "nh": (v / v_max) if v_max else 0.0,
                "label": QDateTime.fromMSecsSinceEpoch(int(b.get("bucketStart", 0))).toString("HH:mm"),
            }
            for v, b in zip(values, buckets)
        ]

    def _update_telemetry_stats(self, values: list[float]) -> None:
        if not values:
            self._tel_stats = {}
            return
        self._tel_stats = {
            "min": f"{min(values):.2f}",
            "max": f"{max(values):.2f}",
            "avg": f"{sum(values) / len(values):.2f}",
            "count": str(len(values)),
        }

    # -- XY Table ------------------------------------------------------------

    def _on_xy_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []
        self._xy_robots_cache = robots
        if self._xy_selected_robot_id not in {r.id for r in robots}:
            self._xy_selected_robot_id = robots[0].id if robots else None
        self.changed.emit()

    def _xy_selected_robot(self) -> RobotView | None:
        for r in self._xy_robots_cache:
            if r.id == self._xy_selected_robot_id:
                return r
        return None

    @Property("QVariantList", notify=changed)
    def xyRobotOptions(self) -> list[dict[str, str]]:
        return [{"id": r.id, "label": f"{r.model} (A{r.id})"} for r in self._xy_robots_cache]

    @Property(str, notify=changed)
    def xySelectedRobotId(self) -> str:
        return self._xy_selected_robot_id or ""

    @Slot(str)
    def selectXyRobot(self, robot_id: str) -> None:
        if robot_id != self._xy_selected_robot_id:
            self._xy_selected_robot_id = robot_id or None
            self.changed.emit()

    @Property(bool, notify=changed)
    def xyHasRobot(self) -> bool:
        return self._xy_selected_robot() is not None

    @Property(bool, notify=changed)
    def xyHasTable(self) -> bool:
        robot = self._xy_selected_robot()
        return robot is not None and robot.has_xy_table

    @Property(bool, notify=changed)
    def xyCanReset(self) -> bool:
        return self.xyHasRobot and self.xyHasTable

    @Property(int, notify=changed)
    def xyWidth(self) -> int:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        size = table["tableSize"] if table else {}
        return int(size.get("width", _XY_DISPLAY_DEFAULT_SIZE_MM))

    @Property(int, notify=changed)
    def xyLength(self) -> int:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        size = table["tableSize"] if table else {}
        return int(size.get("length", _XY_DISPLAY_DEFAULT_SIZE_MM))

    @Property(str, notify=changed)
    def xyPosX(self) -> str:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        pos = table["pos"] if table else {"x": 0, "y": 0}
        return f"{float(pos.get('x', 0)):.2f}"

    @Property(str, notify=changed)
    def xyPosY(self) -> str:
        robot = self._xy_selected_robot()
        table = robot.xy_table if robot is not None else None
        pos = table["pos"] if table else {"x": 0, "y": 0}
        return f"{float(pos.get('y', 0)):.2f}"

    @Property("QVariantList", constant=True)
    def xyJogSteps(self) -> list[float]:
        return list(_XY_JOG_STEPS_MM)

    @Slot(float)
    def setXyJogStep(self, value: float) -> None:
        self._xy_jog_step_mm = value

    @Slot()
    def enableXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        # Matches XYTableConfig.tsx's own handleAddTable() exactly: only
        # the flag, no xyTable block yet - see xy_table_panel.py's own
        # header for why.
        robot.set_has_xy_table(True)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def disableXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        robot.set_has_xy_table(False)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot()
    def resetXyTable(self) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        robot.set_xy_table(_default_xy_table())
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int)
    def setXyWidth(self, value: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return  # matches XYTableConfig.tsx's own handleSizeChange() no-op guard
        table["tableSize"]["width"] = value
        robot.set_xy_table(table)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(int)
    def setXyLength(self, value: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return
        table["tableSize"]["length"] = value
        robot.set_xy_table(table)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str, int)
    def jogXyTable(self, axis: str, direction: int) -> None:
        robot = self._xy_selected_robot()
        if robot is None or axis not in ("x", "y"):
            return
        table = robot.xy_table
        if not table:
            return  # matches XYTableConfig.tsx's own handleJog() no-op guard
        new_value = table["pos"][axis] + direction * self._xy_jog_step_mm
        bound = table["tableSize"]["width" if axis == "x" else "length"]
        new_value = max(0.0, min(new_value, float(bound)))
        table["pos"][axis] = new_value
        robot.set_xy_table(table)
        self._controller.push_active_state()
        self.changed.emit()

    @Slot(str)
    def saveXyTableConfig(self, path: str) -> None:
        robot = self._xy_selected_robot()
        if robot is None:
            return
        table = robot.xy_table
        if not table:
            return
        local_path = QUrl(path).toLocalFile() or path
        if not local_path:
            return
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(table, f, indent=2)

    # -- Overview --------------------------------------------------------

    @Property(str, notify=changed)
    def overviewName(self) -> str:
        return self._overview_name

    @Property(str, notify=changed)
    def overviewIp(self) -> str:
        return self._overview_ip

    @Property(str, notify=changed)
    def overviewRobotCount(self) -> str:
        return self._overview_robot_count

    @Property(str, notify=changed)
    def overviewOnlineCount(self) -> str:
        return self._overview_online_count

    @Property(str, notify=changed)
    def overviewCpu(self) -> str:
        return self._overview_cpu

    @Property(str, notify=changed)
    def overviewMem(self) -> str:
        return self._overview_mem

    @Property(str, notify=changed)
    def overviewTemp(self) -> str:
        return self._overview_temp

    @Property(str, notify=changed)
    def overviewUptime(self) -> str:
        return self._overview_uptime

    @Property("QVariantList", notify=changed)
    def overviewRobots(self) -> list[dict[str, object]]:
        return self._overview_robots

    def _on_overview_metrics_changed(self, metrics: dict) -> None:
        cpu = metrics.get("cpu_load")
        mem = metrics.get("memory_usage")
        temp = metrics.get("temp")
        uptime = metrics.get("uptime")
        self._overview_cpu = f"{cpu}%" if cpu is not None else "-"
        self._overview_mem = f"{mem}%" if mem is not None else "-"
        self._overview_temp = f"{temp:.0f}°C" if isinstance(temp, (int, float)) else "-"
        if isinstance(uptime, (int, float)):
            hours, rem = divmod(int(uptime), 3600)
            minutes = rem // 60
            self._overview_uptime = f"{hours}h {minutes}m"
        else:
            self._overview_uptime = "-"
        self.changed.emit()

    def _on_overview_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        if active is None:
            self._overview_name = "-"
            self._overview_ip = "-"
            self._overview_robot_count = "-"
            self._overview_online_count = "-"
            self._overview_robots = []
            self.changed.emit()
            return
        robots = active.robots
        online = sum(1 for r in robots if r.online)
        self._overview_name = active.name
        self._overview_ip = active.ip
        self._overview_robot_count = str(len(robots))
        self._overview_online_count = f"{online} / {len(robots)}"
        self._overview_robots = [
            {
                "id": r.id,
                "model": r.model,
                "role": r.role,
                "status": _("STATUS_ONLINE") if r.online else _("STATUS_OFFLINE"),
                "online": r.online,
                "speedAccel": f"{r.speed:.0f}% / {r.acceleration:.0f}%",
            }
            for r in robots
        ]
        self.changed.emit()


def run_qtquick() -> int:
    # Same real reason main.py's own classic entry point sets this before
    # constructing its QApplication: Qt6's default rounding policy snaps a
    # fractional OS scale factor (125%/150%/175%, common on a 27"-32" 4K
    # monitor) to the nearest whole integer, which reads as slightly
    # blurry/mis-sized fixed-pixel controls. PassThrough applies the OS's
    # exact factor instead - must be set before the QGuiApplication exists.
    from PySide6.QtCore import Qt

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("HYDRA-UMC SUITE")
    app.setApplicationDisplayName("HYDRA-UMC SUITE")
    app.setOrganizationName("Electro Hobby 3D")
    for icon_path in (IMAGES_DIR / "HYDRA_UMC_ICON.ico", IMAGES_DIR / "HYDRA_UMC_ICON.svg"):
        if icon_path.is_file():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                app.setWindowIcon(icon)
                break
    QQuickStyle.setStyle("Basic")

    # Same qasync integration main.py's own classic entry point already
    # relies on for every `async def` in app.py/net/client.py/
    # net/discovery.py - a QGuiApplication (no QApplication/QtWidgets)
    # needs the same real event-loop wiring, not a different one.
    import asyncio

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = SuiteController()
    bridge = SuiteQtBridge(controller)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("suiteBackend", bridge)
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    if not engine.rootObjects():
        return 1

    with loop:
        return loop.run_forever()


if __name__ == "__main__":
    sys.exit(run_qtquick())
