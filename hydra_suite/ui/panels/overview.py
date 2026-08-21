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

        # GET /api/system/metrics, polled every 5s by HydraConnection - same
        # host CPU/memory/temperature readout HYDRA-UMC-STUDIO's own footer
        # (Dashboard.tsx SystemMetricsBar) and the Android app's Dashboard
        # already show, kept here for parity across all 3 clients.
        metrics_box = QGroupBox(_("GROUP_SYSTEM_METRICS"))
        metrics_layout = QGridLayout(metrics_box)
        self._cpu_label = QLabel("-")
        self._mem_label = QLabel("-")
        self._temp_label = QLabel("-")
        self._uptime_label = QLabel("-")
        for row, (caption, value_label) in enumerate(
            [
                (_("LBL_CPU_LOAD"), self._cpu_label),
                (_("LBL_MEMORY"), self._mem_label),
                (_("LBL_TEMP"), self._temp_label),
                (_("LBL_UPTIME"), self._uptime_label),
            ]
        ):
            cap = QLabel(caption)
            cap.setStyleSheet("color: #7f8ea1;")
            metrics_layout.addWidget(cap, row, 0)
            metrics_layout.addWidget(value_label, row, 1)
        layout.addWidget(metrics_box)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels((_("COL_ROBOT"), _("COL_MODEL"), _("COL_ROLE"), _("COL_STATUS"), _("COL_SPEED_ACCEL")))
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        controller.active_state_changed.connect(self._on_state_changed)
        controller.active_metrics_changed.connect(self._on_metrics_changed)

    def _on_metrics_changed(self, metrics: dict) -> None:
        cpu = metrics.get("cpu_load")
        mem = metrics.get("memory_usage")
        temp = metrics.get("temp")
        uptime = metrics.get("uptime")
        self._cpu_label.setText(f"{cpu}%" if cpu is not None else "-")
        self._mem_label.setText(f"{mem}%" if mem is not None else "-")
        self._temp_label.setText(f"{temp:.0f}°C" if isinstance(temp, (int, float)) else "-")
        if isinstance(uptime, (int, float)):
            hours, rem = divmod(int(uptime), 3600)
            minutes = rem // 60
            self._uptime_label.setText(f"{hours}h {minutes}m")
        else:
            self._uptime_label.setText("-")

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

        if self._table.rowCount() != len(robots):
            self._table.setRowCount(len(robots))
        for row, robot in enumerate(robots):
            self._set_cell(row, 0, robot.id)
            self._set_cell(row, 1, robot.model)
            self._set_cell(row, 2, robot.role)
            self._set_cell(row, 3, _("STATUS_ONLINE") if robot.online else _("STATUS_OFFLINE"))
            self._set_cell(row, 4, f"{robot.speed:.0f}% / {robot.acceleration:.0f}%")

    def _set_cell(self, row: int, col: int, text: str) -> None:
        # active_state_changed fires on every swarm state tick (any robot,
        # any controller, any unrelated field), not only when this specific
        # cell's value changed - same pattern that caused the 3D viewport
        # repaint bug fixed in a previous session. Reusing the existing
        # QTableWidgetItem and only touching it when the text actually
        # differs avoids rebuilding all N*5 cells (Qt model resets/layout
        # work included) on every message from a live swarm, without
        # changing what ends up on screen.
        item = self._table.item(row, col)
        if item is None:
            self._table.setItem(row, col, QTableWidgetItem(text))
        elif item.text() != text:
            item.setText(text)
