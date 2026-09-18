# =============================================================================
# HYDRA-UMC SUITE - ui/panels/trajectory_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Jog-and-record points table, the desktop counterpart to HYDRA-UMC-STUDIO's
# own "record a point / play back a trajectory" workflow (RobotDetail.tsx).
#
# Export/Import now round-trip through HYDRA-UMC-STUDIO's own real
# WORKS/*.json trajectory format (server.ts's own POST /api/upload-work +
# GET /<folder>/index.json, the exact same calls RobotDetail.tsx's own
# handleSaveWorkFile()/fetchWorks() make) - a point recorded here is already
# in that format's own native-joints shape (j1..j6, the same keys
# server.ts's own trajectory validation accepts as an alternative to a
# Cartesian x/y/z/a/b/c pose), so no conversion is needed, only stripping
# this panel's own local "_time" display column before writing. This closes
# the gap this file used to document here and in docs/ROADMAP.md as
# explicitly not done yet.
# =============================================================================
from __future__ import annotations

import asyncio
import re
import time

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
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

        works_row = QHBoxLayout()
        export_button = QPushButton(_("BTN_EXPORT_WORK"))
        export_button.clicked.connect(lambda: asyncio.ensure_future(self._on_export_work()))
        works_row.addWidget(export_button)

        import_button = QPushButton(_("BTN_IMPORT_WORK"))
        import_button.clicked.connect(lambda: asyncio.ensure_future(self._on_import_work()))
        works_row.addWidget(import_button)
        layout.addLayout(works_row)

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

    def _works_folder_path(self) -> str:
        """Same real resolution HYDRA-UMC-STUDIO's own RobotDetail.tsx
        applies: `settings.worksPaths[robot.id]` if the operator configured
        one from Config, else `WORKS/<robot name with whitespace stripped>`
        - so this panel writes to (and reads from) the exact same folder a
        browser tab already uses for this same robot, without needing its
        own separate configuration surface."""
        state = self._controller.active_state
        works_paths = {}
        if state is not None:
            works_paths = (state.raw.get("settings") or {}).get("worksPaths") or {}
        robot_id = self._current_robot.id
        configured = works_paths.get(robot_id)
        if configured:
            return str(configured)
        robot_name = str(self._current_robot.raw.get("name") or robot_id)
        return f"WORKS/{re.sub(r'\s+', '', robot_name)}"

    async def _on_export_work(self) -> None:
        if self._current_robot is None or not self._points:
            return
        conn = self._controller.active_connection
        if conn is None:
            QMessageBox.warning(self, _("HEADING_TRAJECTORY"), _("LBL_ES_NO_ACTIVE_SERVER"))
            return
        file_name, ok = QInputDialog.getText(self, _("DLG_EXPORT_WORK_TITLE"), _("DLG_EXPORT_WORK_LABEL"), text="trajectory_1")
        if not ok or not file_name.strip():
            return
        if not file_name.endswith(".json"):
            file_name += ".json"
        # Strip this panel's own local "_time" display column - STUDIO's
        # own WORKS files never carry it, and server.ts's trajectory
        # validation only recognizes real numeric joint/pose fields plus
        # motionType, so an unknown key would just be dead weight on disk.
        content = [{name: point[name] for name in JOINT_NAMES} for point in self._points]
        folder_path = self._works_folder_path()
        result = await conn.save_work_file(folder_path, file_name, content)
        if result is None:
            QMessageBox.critical(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_EXPORT_FAILED", error="network error"))
            return
        status, body = result
        if status != 200:
            error = body.get("error") if isinstance(body, dict) else str(body)
            QMessageBox.critical(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_EXPORT_FAILED", error=error))
            return
        QMessageBox.information(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_EXPORTED", file=f"{folder_path}/{file_name}"))

    async def _on_import_work(self) -> None:
        if self._current_robot is None:
            return
        conn = self._controller.active_connection
        if conn is None:
            QMessageBox.warning(self, _("HEADING_TRAJECTORY"), _("LBL_ES_NO_ACTIVE_SERVER"))
            return
        folder_path = self._works_folder_path()
        index_result = await conn.fetch_works_index(folder_path)
        if index_result is None or index_result[0] != 200 or not isinstance(index_result[1], list):
            QMessageBox.warning(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_IMPORT_FAILED", error="no Works found for this robot"))
            return
        files: list[str] = [f for f in index_result[1] if isinstance(f, str)]
        if not files:
            QMessageBox.warning(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_IMPORT_FAILED", error="no Works found for this robot"))
            return
        file_name, ok = QInputDialog.getItem(self, _("DLG_IMPORT_WORK_TITLE"), _("DLG_IMPORT_WORK_LABEL"), files, 0, False)
        if not ok or not file_name:
            return
        file_result = await conn.fetch_work_file(folder_path, file_name)
        if file_result is None or file_result[0] != 200 or not isinstance(file_result[1], list):
            QMessageBox.critical(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_IMPORT_FAILED", error=f"could not read {file_name}"))
            return
        # A Work point may be joint-space (j1..j6, this panel's own native
        # shape) or a Cartesian x/y/z/a/b/c pose (STUDIO's own recorded-
        # from-3D-view points) - only points that already carry every real
        # joint value can be jogged back to from this panel (it has no
        # inverse-kinematics engine of its own), so a Cartesian-only point
        # is skipped rather than silently imported as all-zero joints.
        imported: list[dict[str, float]] = []
        skipped = 0
        for raw_point in file_result[1]:
            if not isinstance(raw_point, dict) or not all(name in raw_point for name in JOINT_NAMES):
                skipped += 1
                continue
            point = {name: float(raw_point[name]) for name in JOINT_NAMES}
            point["_time"] = time.strftime("%H:%M:%S")
            imported.append(point)
        if not imported:
            QMessageBox.warning(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_IMPORT_FAILED", error=f"{file_name} has no native-joint points this panel can jog to"))
            return
        self._points = imported
        self._refresh_table()
        if skipped:
            QMessageBox.information(self, _("HEADING_TRAJECTORY"), _("MSG_WORK_IMPORT_PARTIAL", imported=len(imported), skipped=skipped))
