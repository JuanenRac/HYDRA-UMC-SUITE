# =============================================================================
# HYDRA-UMC SUITE - ui/main_window.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The Photoshop-style floating/dockable workspace: every panel is a real
# QDockWidget, which natively supports everything the user asked for -
# drag to float free, drag back to dock/merge into another panel as a
# tab, split the workspace by dropping on an edge, close/minimize
# (float+shrink)/maximize (float+expand) - Qt's own mature docking system,
# not a custom-built one, since QDockWidget already does exactly this and
# a hand-rolled equivalent would just be reinventing it with more bugs.
# =============================================================================
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QActionGroup, QIcon
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from hydra_suite import __version__
from hydra_suite.app import SuiteController
from hydra_suite.i18n import _, AVAILABLE_LANGUAGES, current_language, save_config, CONFIG_FILE_PATH
from hydra_suite.ui.panels.admin_clients_panel import AdminClientsPanel
from hydra_suite.ui.panels.admin_logs_panel import AdminLogsPanel
from hydra_suite.ui.panels.admin_server_panel import AdminServerPanel
from hydra_suite.ui.panels.ai_family_status_panel import AiFamilyStatusPanel
from hydra_suite.ui.panels.cameras_panel import CamerasPanel
from hydra_suite.ui.panels.ecosystem_services_panel import EcosystemServicesPanel
from hydra_suite.ui.panels.ecosystem_telemetry_panel import EcosystemTelemetryPanel
from hydra_suite.ui.panels.logs_panel import LogsPanel
from hydra_suite.ui.panels.overview import OverviewPanel
from hydra_suite.ui.panels.robot_control import RobotControlPanel
from hydra_suite.ui.panels.server_browser import ServerBrowserPanel
from hydra_suite.ui.panels.trajectory_panel import TrajectoryPanel
from hydra_suite.ui.panels.viewport_panel import ViewportPanel
from hydra_suite.ui.qtquick_deck import SuiteDeckBridge

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "images"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HYDRA-UMC SUITE")
        self.setMinimumSize(1920, 1080)
        self._apply_window_icon()

        self.controller = SuiteController(self)

        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
        )
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, self.tabPosition(Qt.DockWidgetArea.LeftDockWidgetArea))

        self._build_menu()
        self._build_panels()
        self._build_command_deck()
        self._build_status_bar()

    def _apply_window_icon(self) -> None:
        """Use the same official HYDRA-UMC mark as the Updater taskbar.

        The ICO is preferred for native Windows title/taskbar integration;
        the SVG remains a portable fallback for a source checkout on Linux.
        Missing artwork must never prevent the control client from starting.
        """
        for candidate in (IMAGES_DIR / "HYDRA_UMC_ICON.ico", IMAGES_DIR / "HYDRA_UMC_ICON.svg"):
            if candidate.is_file():
                icon = QIcon(str(candidate))
                if not icon.isNull():
                    self.setWindowIcon(icon)
                    return

    # --- panels ---------------------------------------------------------------

    def _make_dock(self, title: str, widget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock_{title.lower().replace(' ', '_')}")
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(area, dock)
        return dock

    def _build_panels(self) -> None:
        self.server_browser = ServerBrowserPanel(self.controller)
        self.overview = OverviewPanel(self.controller)
        self.robot_control = RobotControlPanel(self.controller)
        self.viewport_panel = ViewportPanel(self.controller)
        self.trajectory_panel = TrajectoryPanel(self.controller)
        self.cameras_panel = CamerasPanel(self.controller)
        self.logs_panel = LogsPanel()
        # Ecosystem-wide panels - visual surface for the whole HYDRA-UMC-*
        # ecosystem the active connection's own Server can see, not just
        # this controller's own robots. See each panel's own header
        # comment for exactly which real Server route it talks to.
        self.ecosystem_services_panel = EcosystemServicesPanel(self.controller)
        self.ecosystem_telemetry_panel = EcosystemTelemetryPanel(self.controller)
        self.ai_family_status_panel = AiFamilyStatusPanel(self.controller)
        self.admin_clients_panel = AdminClientsPanel(self.controller)
        self.admin_logs_panel = AdminLogsPanel(self.controller)
        self.admin_server_panel = AdminServerPanel(self.controller)

        self.robot_control.robot_selected.connect(self.viewport_panel.set_selected_robot)
        self.robot_control.robot_selected.connect(self.trajectory_panel.set_selected_robot)

        dock_servers = self._make_dock(_("DOCK_SERVERS"), self.server_browser, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_overview = self._make_dock(_("DOCK_OVERVIEW"), self.overview, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_viewport = self._make_dock(_("DOCK_VIEWPORT"), self.viewport_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_robot = self._make_dock(_("DOCK_ROBOT_CONTROL"), self.robot_control, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_traj = self._make_dock(_("DOCK_TRAJECTORY"), self.trajectory_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_cameras = self._make_dock(_("TAB_CAMERAS"), self.cameras_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_logs = self._make_dock(_("DOCK_LOGS"), self.logs_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_es_services = self._make_dock(_("DOCK_ECOSYSTEM_SERVICES"), self.ecosystem_services_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_es_telemetry = self._make_dock(_("DOCK_ECOSYSTEM_TELEMETRY"), self.ecosystem_telemetry_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_ai_family = self._make_dock(_("DOCK_AI_FAMILY"), self.ai_family_status_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_admin_clients = self._make_dock(_("DOCK_ADMIN_CLIENTS"), self.admin_clients_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_admin_logs = self._make_dock(_("DOCK_ADMIN_LOGS"), self.admin_logs_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_admin_server = self._make_dock(_("DOCK_ADMIN_SERVER"), self.admin_server_panel, Qt.DockWidgetArea.BottomDockWidgetArea)

        self._docks = {
            "servers": dock_servers,
            "overview": dock_overview,
            "viewport": dock_viewport,
            "robot": dock_robot,
            "trajectory": dock_traj,
            "cameras": dock_cameras,
            "logs": dock_logs,
            "ecosystem_services": dock_es_services,
            "ecosystem_telemetry": dock_es_telemetry,
            "ai_family": dock_ai_family,
            "admin_clients": dock_admin_clients,
            "admin_logs": dock_admin_logs,
            "admin_server": dock_admin_server,
        }

        # Sensible default arrangement - the user is free to drag any of
        # these into any other configuration afterward (float/merge/
        # split/close), this is just where they start.
        self.tabifyDockWidget(dock_servers, dock_overview)
        dock_servers.raise_()
        self.splitDockWidget(dock_viewport, dock_robot, Qt.Orientation.Horizontal)
        self.resizeDocks([dock_viewport, dock_robot], [1200, 600], Qt.Orientation.Horizontal)
        self.tabifyDockWidget(dock_traj, dock_cameras)
        self.tabifyDockWidget(dock_cameras, dock_logs)
        # The 5 new ecosystem/admin panels start tabbed together, behind
        # the existing bottom-area tab group - visible via the View menu
        # or a click, not competing for screen space with the per-robot
        # panels above by default.
        self.tabifyDockWidget(dock_logs, dock_es_services)
        self.tabifyDockWidget(dock_es_services, dock_es_telemetry)
        self.tabifyDockWidget(dock_es_telemetry, dock_ai_family)
        self.tabifyDockWidget(dock_ai_family, dock_admin_clients)
        self.tabifyDockWidget(dock_admin_clients, dock_admin_logs)
        self.tabifyDockWidget(dock_admin_logs, dock_admin_server)
        dock_traj.raise_()

        # A dock closed via its own [x] button would otherwise be gone for
        # good until the app restarts - toggleViewAction() gives each one
        # a real "show again" entry in the View menu, same as a plain Qt
        # app with dockable panels normally does.
        for dock in (
            dock_servers, dock_overview, dock_viewport, dock_robot, dock_traj, dock_cameras, dock_logs,
            dock_es_services, dock_es_telemetry, dock_ai_family, dock_admin_clients, dock_admin_logs, dock_admin_server,
        ):
            self._view_menu.addAction(dock.toggleViewAction())

    # --- command deck -------------------------------------------------------

    def _build_command_deck(self) -> None:
        """Host Updater's Qt Quick engine over Suite's real dock actions."""
        deck = QToolBar(_("TOPBAR_PRODUCT"), self)
        deck.setObjectName("commandDeck")
        deck.setMovable(False)
        deck.setFloatable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, deck)
        self._command_deck = deck

        qml_path = ASSETS_DIR / "qml" / "CommandDeck.qml"
        logo_path = IMAGES_DIR / "HYDRA_UMC_ICON.svg"
        self._deck_bridge = SuiteDeckBridge(
            title=_("TOPBAR_PRODUCT"),
            version=__version__,
            logo_source=QUrl.fromLocalFile(str(logo_path)).toString(),
        )
        self._deck_bridge.navigateRequested.connect(self._on_deck_navigation)
        self._deck_bridge.aboutRequested.connect(self._show_about)
        quick_deck = QQuickWidget(deck)
        quick_deck.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        # ``required property`` is initialized at QML object construction;
        # a context property arrives too late for that validation step.
        quick_deck.setInitialProperties({"deckBackend": self._deck_bridge})
        quick_deck.setSource(QUrl.fromLocalFile(str(qml_path)))
        quick_deck.setMinimumWidth(1040)
        quick_deck.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        deck.addWidget(quick_deck)
        self._quick_deck = quick_deck

        self.controller.active_status_changed.connect(self._update_command_deck_status)
        self.controller.active_connection_changed.connect(self._update_command_deck_target)
        self._update_command_deck_status("disconnected")
        self._update_command_deck_target("")
        self._update_command_deck_clock()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_command_deck_clock)
        self._clock_timer.start(1000)

    def _on_deck_navigation(self, key: str) -> None:
        if key == "about":
            self._show_about()
        elif key in self._docks:
            self._activate_dock(key)

    def _activate_dock(self, key: str) -> None:
        dock = self._docks[key]
        dock.show()
        dock.raise_()

    def _update_command_deck_status(self, status: str) -> None:
        status_key = {
            "connected": "TOPBAR_STATUS_CONNECTED",
            "connecting": "TOPBAR_STATUS_CONNECTING",
            "error": "TOPBAR_STATUS_ERROR",
        }.get(status, "TOPBAR_STATUS_DISCONNECTED")
        colour = {
            "connected": "#43db9b",
            "connecting": "#f3ba55",
            "error": "#ee6b80",
        }.get(status, "#91a8bd")
        self._deck_bridge.set_status(_(status_key), colour)

    def _update_command_deck_target(self, connection_id: str) -> None:
        target = connection_id or _("TOPBAR_NO_TARGET")
        self._deck_bridge.set_target(target)

    def _update_command_deck_clock(self) -> None:
        self._deck_bridge.set_clock(f"{datetime.now(timezone.utc):%H:%M:%S} UTC")

    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu(_("MENU_FILE"))
        quit_action = file_menu.addAction(_("MENU_QUIT"))
        quit_action.triggered.connect(self.close)

        view_menu = menu.addMenu(_("MENU_VIEW"))
        self._view_menu = view_menu  # populated in _build_panels via dock.toggleViewAction()

        language_menu = menu.addMenu(_("MENU_LANGUAGE"))
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        active_lang = current_language()
        for code, display in AVAILABLE_LANGUAGES:
            action = language_menu.addAction(display)
            action.setCheckable(True)
            action.setChecked(code == active_lang)
            action.triggered.connect(lambda checked=False, c=code: self._on_language_change(c))
            language_group.addAction(action)

        help_menu = menu.addMenu(_("MENU_HELP"))
        about_action = help_menu.addAction(_("MENU_ABOUT"))
        about_action.triggered.connect(self._show_about)

    def _build_status_bar(self) -> None:
        self._status = self.statusBar()
        self._status.showMessage(_("STATUS_READY"))
        self.controller.active_status_changed.connect(
            lambda status: self._status.showMessage(_("STATUS_ACTIVE_CONNECTION", status=status))
        )
        # HydraConnection.error (net/client.py) - initial-fetch/push_state()
        # failures - used to have nothing connected to it anywhere in the UI,
        # so a jog/camera-toggle/trajectory-point write that failed to reach
        # the server looked identical to a successful one. A temporary status
        # bar message is a deliberately lightweight surface (no modal to
        # dismiss on every reconnect blip); the Server Browser panel's own
        # per-row "Login failed" status already covers the persistent,
        # per-server case for auth specifically.
        self.controller.connection_error.connect(
            lambda conn_id, message: self._status.showMessage(f"[{conn_id}] {message}", 8000)
        )

    def _show_about(self) -> None:
        QMessageBox.information(self, _("TITLE_ABOUT"), _("MSG_ABOUT_BODY", version=__version__))

    def _on_language_change(self, code: str) -> None:
        if save_config({"language": code}):
            QMessageBox.information(self, _("TITLE_RESTART_NEEDED"), _("MSG_RESTART_NEEDED"))
        else:
            QMessageBox.critical(self, _("TITLE_COULDNT_SAVE"), _("MSG_LANGUAGE_NOT_SAVED", path=str(CONFIG_FILE_PATH)))

    def closeEvent(self, event) -> None:
        asyncio.ensure_future(self.controller.shutdown())
        super().closeEvent(event)
