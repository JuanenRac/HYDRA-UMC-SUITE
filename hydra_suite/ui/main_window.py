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
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMessageBox

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _, AVAILABLE_LANGUAGES, current_language, save_config, CONFIG_FILE_PATH
from hydra_suite.ui.panels.cameras_panel import CamerasPanel
from hydra_suite.ui.panels.overview import OverviewPanel
from hydra_suite.ui.panels.robot_control import RobotControlPanel
from hydra_suite.ui.panels.server_browser import ServerBrowserPanel
from hydra_suite.ui.panels.trajectory_panel import TrajectoryPanel
from hydra_suite.ui.panels.viewport_panel import ViewportPanel

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HYDRA-UMC SUITE")
        self.setMinimumSize(1920, 1080)

        self.controller = SuiteController(self)

        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
        )
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, self.tabPosition(Qt.DockWidgetArea.LeftDockWidgetArea))

        self._build_menu()
        self._build_panels()
        self._build_status_bar()

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

        self.robot_control.robot_selected.connect(self.viewport_panel.set_selected_robot)
        self.robot_control.robot_selected.connect(self.trajectory_panel.set_selected_robot)

        dock_servers = self._make_dock(_("DOCK_SERVERS"), self.server_browser, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_overview = self._make_dock(_("DOCK_OVERVIEW"), self.overview, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_viewport = self._make_dock(_("DOCK_VIEWPORT"), self.viewport_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_robot = self._make_dock(_("DOCK_ROBOT_CONTROL"), self.robot_control, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_traj = self._make_dock(_("DOCK_TRAJECTORY"), self.trajectory_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        dock_cameras = self._make_dock(_("TAB_CAMERAS"), self.cameras_panel, Qt.DockWidgetArea.BottomDockWidgetArea)

        # Sensible default arrangement - the user is free to drag any of
        # these into any other configuration afterward (float/merge/
        # split/close), this is just where they start.
        self.tabifyDockWidget(dock_servers, dock_overview)
        dock_servers.raise_()
        self.splitDockWidget(dock_viewport, dock_robot, Qt.Orientation.Horizontal)
        self.resizeDocks([dock_viewport, dock_robot], [1200, 600], Qt.Orientation.Horizontal)
        self.tabifyDockWidget(dock_traj, dock_cameras)
        dock_traj.raise_()

        # A dock closed via its own [x] button would otherwise be gone for
        # good until the app restarts - toggleViewAction() gives each one
        # a real "show again" entry in the View menu, same as a plain Qt
        # app with dockable panels normally does.
        for dock in (dock_servers, dock_overview, dock_viewport, dock_robot, dock_traj, dock_cameras):
            self._view_menu.addAction(dock.toggleViewAction())

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
        QMessageBox.information(self, _("TITLE_ABOUT"), _("MSG_ABOUT_BODY"))

    def _on_language_change(self, code: str) -> None:
        if save_config({"language": code}):
            QMessageBox.information(self, _("TITLE_RESTART_NEEDED"), _("MSG_RESTART_NEEDED"))
        else:
            QMessageBox.critical(self, _("TITLE_COULDNT_SAVE"), _("MSG_LANGUAGE_NOT_SAVED", path=str(CONFIG_FILE_PATH)))

    def closeEvent(self, event) -> None:
        asyncio.ensure_future(self.controller.shutdown())
        super().closeEvent(event)
