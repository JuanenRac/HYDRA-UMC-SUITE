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
import sys
from dataclasses import dataclass
from pathlib import Path

import qasync
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from hydra_suite import __version__, logging_handler
from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, ServerInfo
from hydra_suite.net.discovery import DEFAULT_PORT, discover_servers
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
MIGRATED_PANELS = frozenset({"logs", "overview", "servers"})

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


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
