# =============================================================================
# HYDRA-UMC SUITE - ui/panels/overview.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Headline summary of the active connection - the desktop counterpart to
# HYDRA-UMC-STUDIO's own OverviewPanel (Dashboard.tsx) showing per-robot
# online/model/status cards, reimplemented as a table here rather than a
# card grid (a table scales better to a swarm-scale robot count across
# multiple controllers than repeating a card layout would).
# =============================================================================
from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState


class OverviewPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel(_("HEADING_OVERVIEW"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        stats_box = QGroupBox(_("GROUP_ACTIVE_CONTROLLER"))
        stats_layout = QGridLayout(stats_box)
        self._name_label = QLabel("-")
        self._ip_label = QLabel("-")
        self._robot_count_label = QLabel("-")
        self._online_count_label = QLabel("-")
        for row, (caption, value_label) in enumerate(
            [
                (_("LBL_NAME"), self._name_label),
                (_("LBL_IP"), self._ip_label),
                (_("LBL_ROBOTS"), self._robot_count_label),
                (_("LBL_ONLINE"), self._online_count_label),
            ]
        ):
            cap = QLabel(caption)
            cap.setStyleSheet("color: #7f8ea1;")
            stats_layout.addWidget(cap, row, 0)
            stats_layout.addWidget(value_label, row, 1)
        layout.addWidget(stats_box)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels((_("COL_ROBOT"), _("COL_MODEL"), _("COL_ROLE"), _("COL_STATUS"), _("COL_SPEED_ACCEL")))
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        controller.active_state_changed.connect(self._on_state_changed)

    def _on_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        if active is None:
            self._name_label.setText("-")
            self._ip_label.setText("-")
            self._robot_count_label.setText("-")
            self._online_count_label.setText("-")
            self._table.setRowCount(0)
            return

        robots = active.robots
        online = sum(1 for r in robots if r.online)
        self._name_label.setText(active.name)
        self._ip_label.setText(active.ip)
        self._robot_count_label.setText(str(len(robots)))
        self._online_count_label.setText(f"{online} / {len(robots)}")

        self._table.setRowCount(len(robots))
        for row, robot in enumerate(robots):
            self._table.setItem(row, 0, QTableWidgetItem(robot.id))
            self._table.setItem(row, 1, QTableWidgetItem(robot.model))
            self._table.setItem(row, 2, QTableWidgetItem(robot.role))
            status_item = QTableWidgetItem(_("STATUS_ONLINE") if robot.online else _("STATUS_OFFLINE"))
            self._table.setItem(row, 3, status_item)
            self._table.setItem(row, 4, QTableWidgetItem(f"{robot.speed:.0f}% / {robot.acceleration:.0f}%"))
