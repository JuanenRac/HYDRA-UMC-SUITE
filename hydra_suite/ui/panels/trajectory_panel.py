# =============================================================================
# HYDRA-UMC SUITE - ui/panels/trajectory_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Jog-and-record points table, the desktop counterpart to HYDRA-UMC-STUDIO's
# own "record a point / play back a trajectory" workflow (RobotDetail.tsx).
# Scope note (see docs/ROADMAP.md): this first pass is a local-only point
# recorder (record the SELECTED robot's current joint pose, jog back to a
# recorded point on demand) - it does NOT yet read/write HYDRA-UMC-STUDIO's
# own WORKS/*.json trajectory file format, so a point recorded here isn't
# visible from the browser UI's own Works library yet. Said honestly here
# rather than implied as full parity.
# =============================================================================
from __future__ import annotations

import time

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import JOINT_NAMES, RobotView


class TrajectoryPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_robot: RobotView | None = None
        self._points: list[dict[str, float]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel(_("HEADING_TRAJECTORY"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        self._robot_label = QLabel(_("LBL_NO_ROBOT_SELECTED"))
        self._robot_label.setStyleSheet("color: #7f8ea1;")
        layout.addWidget(self._robot_label)

        self._table = QTableWidget(0, len(JOINT_NAMES) + 1)
        self._table.setHorizontalHeaderLabels((_("COL_TIME"), *[n.upper() for n in JOINT_NAMES]))
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        self._record_button = QPushButton(_("BTN_RECORD_POSE"))
        self._record_button.setObjectName("primaryAction")
        self._record_button.clicked.connect(self._on_record)
        button_row.addWidget(self._record_button)

        apply_button = QPushButton(_("BTN_JOG_TO_POINT"))
        apply_button.clicked.connect(self._on_apply)
        button_row.addWidget(apply_button)

        delete_button = QPushButton(_("BTN_DELETE_POINT"))
        delete_button.setObjectName("dangerAction")
        delete_button.clicked.connect(self._on_delete)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        self.setEnabled(False)

    def set_selected_robot(self, robot: RobotView | None) -> None:
        # robot_control.py's own _on_state_changed re-emits robot_selected on
        # EVERY active_state_changed tick (any robot in the swarm moving, not
        # just a real selection change) so it always carries a fresh RobotView
        # bound to the current HydraState's own dict - always adopt it, or a
        # later push_active_state() from this panel would silently write into
        # an orphaned dict from a HydraState the connection already replaced.
        # But only reset the recorded points/table when the SELECTED ROBOT
        # itself actually changed - wiping self._points unconditionally here
        # erased every recorded point within moments of recording it against
        # a live server, since a state tick arrives constantly.
        new_id = robot.id if robot else None
        old_id = self._current_robot.id if self._current_robot else None
        self._current_robot = robot
        if new_id != old_id:
            self._points = []
            self._refresh_table()
        self.setEnabled(robot is not None)
        self._robot_label.setText(_("LBL_ROBOT_SELECTED", id=robot.id, model=robot.model) if robot else _("LBL_NO_ROBOT_SELECTED"))

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._points))
        for row, point in enumerate(self._points):
            self._table.setItem(row, 0, QTableWidgetItem(point["_time"]))
            for col, name in enumerate(JOINT_NAMES, start=1):
                self._table.setItem(row, col, QTableWidgetItem(f"{point[name]:.2f}"))

    def _on_record(self) -> None:
        if self._current_robot is None:
            return
        point = dict(self._current_robot.joints)
        point["_time"] = time.strftime("%H:%M:%S")
        self._points.append(point)
        self._refresh_table()
        self._table.selectRow(len(self._points) - 1)

    def _on_apply(self) -> None:
        if self._current_robot is None:
            return
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        point = self._points[rows[0].row()]
        for name in JOINT_NAMES:
            self._current_robot.set_joint(name, point[name])
        self._controller.push_active_state()

    def _on_delete(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        del self._points[rows[0].row()]
        self._refresh_table()
