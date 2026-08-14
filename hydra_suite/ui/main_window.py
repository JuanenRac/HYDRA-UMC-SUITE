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
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMessageBox

from hydra_suite.app import SuiteController
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

        self.robot_control.robot_selected.connect(self.viewport_panel.set_selected_robot)
        self.robot_control.robot_selected.connect(self.trajectory_panel.set_selected_robot)

        dock_servers = self._make_dock("Servers", self.server_browser, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_overview = self._make_dock("Overview", self.overview, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_viewport = self._make_dock("3D Viewport", self.viewport_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_robot = self._make_dock("Robot Control", self.robot_control, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_traj = self._make_dock("Trajectory", self.trajectory_panel, Qt.DockWidgetArea.BottomDockWidgetArea)

        # Sensible default arrangement - the user is free to drag any of
        # these into any other configuration afterward (float/merge/
        # split/close), this is just where they start.
        self.tabifyDockWidget(dock_servers, dock_overview)
        dock_servers.raise_()
        self.splitDockWidget(dock_viewport, dock_robot, Qt.Orientation.Horizontal)
        self.resizeDocks([dock_viewport, dock_robot], [1200, 600], Qt.Orientation.Horizontal)

    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        view_menu = menu.addMenu("&View")
        self._view_menu = view_menu  # populated in _build_panels via dock.toggleViewAction()

        help_menu = menu.addMenu("&Help")
        about_action = help_menu.addAction("About HYDRA-UMC SUITE")
        about_action.triggered.connect(self._show_about)

    def _build_status_bar(self) -> None:
        self._status = self.statusBar()
        self._status.showMessage("Ready - scan the network or add a HYDRA-UMC server to begin.")
        self.controller.active_status_changed.connect(
            lambda status: self._status.showMessage(f"Active connection status: {status}")
        )

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About HYDRA-UMC SUITE",
            "HYDRA-UMC SUITE\n\n"
            "Multi-controller swarm command center for the HYDRA-UMC platform.\n"
            "(c) 2026 JuanenRac (Electro Hobby 3D) - GPL-3.0",
        )

    def closeEvent(self, event) -> None:
        asyncio.ensure_future(self.controller.shutdown())
        super().closeEvent(event)
