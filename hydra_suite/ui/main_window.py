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

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QActionGroup, QIcon
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from hydra_suite import __version__
from hydra_suite.app import SuiteController
from hydra_suite.ui.about_dialog import AboutDialog
from hydra_suite.i18n import _, AVAILABLE_LANGUAGES, current_language, save_config, CONFIG_FILE_PATH
from hydra_suite.ui.panels.admin_clients_panel import AdminClientsPanel
from hydra_suite.ui.panels.admin_logs_panel import AdminLogsPanel
from hydra_suite.ui.panels.admin_server_panel import AdminServerPanel
from hydra_suite.ui.panels.ai_family_status_panel import AiFamilyStatusPanel
from hydra_suite.ui.panels.cameras_panel import CamerasPanel
from hydra_suite.ui.panels.cnc_panel import CncPanel
from hydra_suite.ui.panels.ecosystem_services_panel import EcosystemServicesPanel
from hydra_suite.ui.panels.ecosystem_telemetry_panel import EcosystemTelemetryPanel
from hydra_suite.ui.panels.heated_bed_panel import HeatedBedPanel
from hydra_suite.ui.panels.laser_panel import LaserPanel
from hydra_suite.ui.panels.logs_panel import LogsPanel
from hydra_suite.ui.panels.overview import OverviewPanel
from hydra_suite.ui.panels.robot_control import RobotControlPanel
from hydra_suite.ui.panels.server_browser import ServerBrowserPanel
from hydra_suite.ui.panels.trajectory_panel import TrajectoryPanel
from hydra_suite.ui.panels.viewport_panel import ViewportPanel

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
        # Tool-attachment config panels - ports of HYDRA-UMC-STUDIO's own
        # CNC.tsx/Laser.tsx/HeatedBedConfig.tsx (see module_config_panel.py's
        # own header for the shared implementation and what's deliberately
        # not ported yet - the live 3D preview). 3 of 11 panels from
        # [[project_suite_studio_parity_gap]] done; HeatedBedPanel extends
        # ModuleConfigPanel's own extension hooks for its extra heating
        # controls rather than duplicating the shared shape.
        self.cnc_panel = CncPanel(self.controller)
        self.laser_panel = LaserPanel(self.controller)
        self.heated_bed_panel = HeatedBedPanel(self.controller)

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
        dock_cnc = self._make_dock(_("HEADING_CNC"), self.cnc_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_laser = self._make_dock(_("HEADING_LASER"), self.laser_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_heated_bed = self._make_dock(_("HEADING_HEATED_BED"), self.heated_bed_panel, Qt.DockWidgetArea.BottomDockWidgetArea)

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
            "cnc": dock_cnc,
            "laser": dock_laser,
            "heated_bed": dock_heated_bed,
        }

        # Sensible default arrangement - the user is free to drag any of
        # these into any other configuration afterward (float/merge/
        # split/close), this is just where they start.
        self.tabifyDockWidget(dock_servers, dock_overview)
        dock_servers.raise_()
        self.splitDockWidget(dock_viewport, dock_robot, Qt.Orientation.Horizontal)
        self.resizeDocks([dock_viewport, dock_robot], [1200, 600], Qt.Orientation.Horizontal)
        # The top row (Servers/Overview/3D Viewport/Robot Control) is the
        # workspace that actually needs vertical room - Robot Control's own
        # J1-J6 jog sliders plus Playback/Acceleration ran out of height and
        # got clipped under the default 50/50 split QMainWindow falls back
        # to, while the bottom tab group's own content (one panel visible
        # at a time) never needed anywhere near that much space.
        self.resizeDocks([dock_viewport, dock_traj], [700, 260], Qt.Orientation.Vertical)
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
        self.tabifyDockWidget(dock_admin_server, dock_cnc)
        self.tabifyDockWidget(dock_cnc, dock_laser)
        self.tabifyDockWidget(dock_laser, dock_heated_bed)
        dock_traj.raise_()

        # A dock closed via its own [x] button would otherwise be gone for
        # good until the app restarts - toggleViewAction() gives each one
        # a real "show again" entry in the View menu, same as a plain Qt
        # app with dockable panels normally does.
        for dock in (
            dock_servers, dock_overview, dock_viewport, dock_robot, dock_traj, dock_cameras, dock_logs,
            dock_es_services, dock_es_telemetry, dock_ai_family, dock_admin_clients, dock_admin_logs, dock_admin_server,
            dock_cnc, dock_laser, dock_heated_bed,
        ):
            self._view_menu.addAction(dock.toggleViewAction())

    # --- command deck -------------------------------------------------------

    def _build_command_deck(self) -> None:
        """Build the visual command deck without inventing a second UI.

        Real QToolBar/QLabel/QToolButton widgets, not a Qt Quick/QML
        island - a QQuickWidget embedded inside a QToolBar inside this
        QMainWindow's real QDockWidget layout rendered as a solid black
        rectangle in practice (its own OpenGL/RHI surface never composited
        correctly once the toolbar/dock layout settled), even though the
        exact same QML renders fine in HYDRA-UMC-UPDATER - because that
        app is a pure QQmlApplicationEngine window with no competing
        QMainWindow/QDockWidget widget tree around it. Reverted to the
        plain-widget deck (matches this file's own docstring: real
        QDockWidget panels, not a second, parallel UI toolkit for the bar
        above them) - see CHANGELOG.md for the full account.

        Each navigation control raises one of the application's existing,
        dockable panels. That keeps the game-console presentation useful:
        it is a quick route to real Server, Robot, Camera and Log surfaces,
        while the operator can still rearrange every dock freely afterwards.
        """
        deck = QToolBar(_("TOPBAR_PRODUCT"), self)
        deck.setObjectName("commandDeck")
        deck.setMovable(False)
        deck.setFloatable(False)
        deck.setIconSize(QSize(34, 34))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, deck)
        self._command_deck = deck

        # QIcon is intentionally used for the native title/taskbar icon
        # above, where Windows expects a static ICO. In the visible command
        # deck, QSvgWidget owns the original SVG's QSvgRenderer instead, so
        # its SMIL animateTransform receives repaint requests and remains
        # animated at runtime.
        logo_path = IMAGES_DIR / "HYDRA_UMC_ICON.svg"
        if logo_path.is_file():
            brand = QSvgWidget(str(logo_path), deck)
            brand.renderer().setAnimationEnabled(True)
        else:
            brand = QLabel("H", deck)
        brand.setObjectName("suiteBrand")
        brand.setToolTip(_("TOPBAR_PRODUCT"))
        brand.setFixedSize(44, 44)
        deck.addWidget(brand)

        title = QLabel(_("TOPBAR_PRODUCT"), deck)
        title.setObjectName("commandDeckTitle")
        deck.addWidget(title)
        deck.addSeparator()

        self._add_deck_navigation("DOCK_OVERVIEW", "overview")
        self._add_deck_navigation("DOCK_ROBOT_CONTROL", "robot")
        self._add_deck_navigation("TAB_CAMERAS", "cameras")
        self._add_deck_navigation("DOCK_TRAJECTORY", "trajectory")
        self._add_deck_navigation("DOCK_LOGS", "logs")

        spacer = QWidget(deck)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        deck.addWidget(spacer)

        self._state_chip = QLabel(deck)
        self._state_chip.setObjectName("commandDeckState")
        deck.addWidget(self._state_chip)

        self._target_chip = QLabel(deck)
        self._target_chip.setObjectName("commandDeckTarget")
        deck.addWidget(self._target_chip)

        self._clock_chip = QLabel(deck)
        self._clock_chip.setObjectName("commandDeckClock")
        deck.addWidget(self._clock_chip)

        about = QToolButton(deck)
        about.setObjectName("commandDeckAbout")
        about.setText(_("MENU_ABOUT"))
        about.clicked.connect(self._show_about)
        deck.addWidget(about)

        self.controller.active_status_changed.connect(self._update_command_deck_status)
        self.controller.active_connection_changed.connect(self._update_command_deck_target)
        self._update_command_deck_status("disconnected")
        self._update_command_deck_target("")
        self._update_command_deck_clock()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_command_deck_clock)
        self._clock_timer.start(1000)

    def _add_deck_navigation(self, label_key: str, dock_key: str) -> None:
        button = QToolButton(self._command_deck)
        button.setObjectName("commandDeckNav")
        button.setText(_(label_key))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.clicked.connect(lambda _checked=False, key=dock_key: self._activate_dock(key))
        self._command_deck.addWidget(button)

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
        self._state_chip.setText(f"{_('TOPBAR_SYSTEM_STATE')}\n● {_(status_key)}")
        self._state_chip.setStyleSheet(f"color: {colour};")

    def _update_command_deck_target(self, connection_id: str) -> None:
        target = connection_id or _("TOPBAR_NO_TARGET")
        self._target_chip.setText(f"{_('TOPBAR_ACTIVE_TARGET')}\n{target}")

    def _update_command_deck_clock(self) -> None:
        self._clock_chip.setText(f"{_('TOPBAR_UTC')}\n{datetime.now(timezone.utc):%H:%M:%S}")

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
        logo_path = IMAGES_DIR / "HYDRA_UMC_ICON.svg"
        AboutDialog(__version__, logo_path, self).exec()

    def _on_language_change(self, code: str) -> None:
        if save_config({"language": code}):
            QMessageBox.information(self, _("TITLE_RESTART_NEEDED"), _("MSG_RESTART_NEEDED"))
        else:
            QMessageBox.critical(self, _("TITLE_COULDNT_SAVE"), _("MSG_LANGUAGE_NOT_SAVED", path=str(CONFIG_FILE_PATH)))

    def closeEvent(self, event) -> None:
        asyncio.ensure_future(self.controller.shutdown())
        super().closeEvent(event)
