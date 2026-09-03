# =============================================================================
# HYDRA-UMC SUITE - ui/panels/xy_table_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own XYTableConfig.tsx (294 lines) - the
# 6th of 11 panels from the real, standing SUITE/STUDIO parity gap (see
# [[project_suite_studio_parity_gap]]). NOT built on module_config_panel.py's
# shared ModuleConfigPanel: STUDIO keeps `hasXYTable: boolean` and
# `xyTable: {...}` as two GENUINELY SEPARATE fields (unlike every
# ModuleConfigPanel-family module's single `{enabled, size, ...}` shape,
# and unlike atc_tools_panel.py's own "presence of the key IS the state"
# shape too) - `handleAddTable()` sets only `hasXYTable: true` and writes
# no `xyTable` block at all, so a real robot can be "has an XY table" with
# no table config object yet. STUDIO's own source has a real, faithfully
# reproduced quirk here, not smoothed over: `handleJog()`/`handleSizeChange()`
# both no-op (`if (... || !xyTable) return`) until `xyTable` genuinely
# exists - only `handleReset()` unconditionally creates one. In practice
# that means Enable -> Reset is the real, required first sequence before
# jog/size do anything; this port mirrors that exactly rather than
# "fixing" it here, since the honest port of a real quirk belongs in
# STUDIO's own CHANGELOG if it's ever addressed, not silently diverged
# from on this side.
#
# Also reproduces the real two-different-defaults quirk this surfaced
# (same shape as vacuum_table_panel.py's own real find): the display
# fallback for an unset tableSize is 500mm (`xyTable?.tableSize.width ||
# 500`) but `handleReset()` itself writes 300mm - two different numbers
# for the same field, kept apart deliberately (_DISPLAY_DEFAULT_SIZE_MM
# vs _RESET_SIZE_MM below).
#
# Deliberately does NOT port the right-hand "3D Live View"
# (`XYTableVisualizer`, a react-three-fiber scene) - same real, separate
# omission as every panel in this family (see module_config_panel.py's
# own header for the full reasoning); this panel's own real config
# surface (enable/disable, size, jog, save) is unaffected.
#
# Writes via push_active_state(), matching STUDIO's own updateRobot().
# =============================================================================
from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, RobotView

# Matches XYTableConfig.tsx's own `xyTable?.tableSize.width || 500` -
# what shows in the size fields before any real xyTable object exists.
_DISPLAY_DEFAULT_SIZE_MM = 500
# Matches XYTableConfig.tsx's own handleReset() - what Reset actually
# writes. Deliberately different from the display default above - see
# this file's own header.
_RESET_SIZE_MM = 300

JOG_STEPS_MM: tuple[float, ...] = (0.01, 0.1, 1.0, 2.0, 5.0, 10.0, 100.0)


def _default_xy_table() -> dict:
    return {
        "pos": {"x": 0, "y": 0},
        "tableSize": {"width": _RESET_SIZE_MM, "length": _RESET_SIZE_MM},
        "worldPos": {"x": 0, "y": 0},
        "worldRot": 0,
        "renderScale": 1,
    }


class XYTablePanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_robot: RobotView | None = None
        self._jog_step_mm: float = 10.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        heading = QLabel(_("HEADING_XY_TABLE"))
        heading.setObjectName("panelHeading")
        top_row.addWidget(heading)
        top_row.addStretch(1)
        self._reset_btn = QPushButton(_("BTN_RESET_MODULE"))
        self._reset_btn.clicked.connect(self._on_reset)
        top_row.addWidget(self._reset_btn)
        self._robot_combo = QComboBox()
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        top_row.addWidget(self._robot_combo)
        layout.addLayout(top_row)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # Page 0: no XY table configured yet.
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        empty_title = QLabel(_("LBL_NO_MODULE_ASSIGNED", machine="XY Table"))
        empty_title.setStyleSheet("font-weight: 600; color: #cfd8e3;")
        empty_layout.addWidget(empty_title)
        empty_desc = QLabel(_("LBL_NO_MODULE_DESC"))
        empty_desc.setWordWrap(True)
        empty_desc.setStyleSheet("color: #7f8ea1;")
        empty_layout.addWidget(empty_desc)
        self._enable_btn = QPushButton(_("BTN_ENABLE_MODULE", machine="XY Table"))
        self._enable_btn.clicked.connect(self._on_enable)
        empty_layout.addWidget(self._enable_btn)
        empty_layout.addStretch(2)
        self._stack.addWidget(empty_page)

        # Page 1: table settings + jog.
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)

        settings_box = QGroupBox(_("GROUP_MODULE_SETTINGS"))
        settings_box_layout = QVBoxLayout(settings_box)

        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        self._remove_btn = QPushButton(_("BTN_REMOVE_MODULE"))
        self._remove_btn.setStyleSheet("color: #f43f5e;")
        self._remove_btn.clicked.connect(self._on_disable)
        remove_row.addWidget(self._remove_btn)
        settings_box_layout.addLayout(remove_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel(_("LBL_WIDTH_X")))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(100, 5000)
        self._width_spin.setSingleStep(10)
        self._width_spin.setSuffix(" mm")
        self._width_spin.valueChanged.connect(self._on_width_changed)
        size_row.addWidget(self._width_spin)
        size_row.addWidget(QLabel(_("LBL_LENGTH_Y")))
        self._length_spin = QSpinBox()
        self._length_spin.setRange(100, 5000)
        self._length_spin.setSingleStep(10)
        self._length_spin.setSuffix(" mm")
        self._length_spin.valueChanged.connect(self._on_length_changed)
        size_row.addWidget(self._length_spin)
        settings_box_layout.addLayout(size_row)
        settings_layout.addWidget(settings_box)

        jog_box = QGroupBox(_("GROUP_JOG_CONTROL"))
        jog_box_layout = QVBoxLayout(jog_box)

        step_row = QHBoxLayout()
        step_row.addWidget(QLabel(_("LBL_STEP")))
        self._step_combo = QComboBox()
        for step in JOG_STEPS_MM:
            self._step_combo.addItem(f"{step:g} mm", step)
        self._step_combo.setCurrentIndex(JOG_STEPS_MM.index(10.0))
        self._step_combo.currentIndexChanged.connect(self._on_step_combo_changed)
        step_row.addWidget(self._step_combo)
        step_row.addStretch(1)
        jog_box_layout.addLayout(step_row)

        axes_row = QHBoxLayout()

        x_col = QVBoxLayout()
        x_col.addWidget(QLabel("X Axis"))
        self._x_pos_label = QLabel("0.00")
        self._x_pos_label.setStyleSheet("font-family: monospace; font-size: 16px; color: #f59e0b;")
        x_col.addWidget(self._x_pos_label)
        x_btn_row = QHBoxLayout()
        self._x_minus_btn = QPushButton("◀")
        self._x_minus_btn.clicked.connect(lambda: self._on_jog("x", -1))
        self._x_plus_btn = QPushButton("▶")
        self._x_plus_btn.clicked.connect(lambda: self._on_jog("x", 1))
        x_btn_row.addWidget(self._x_minus_btn)
        x_btn_row.addWidget(self._x_plus_btn)
        x_col.addLayout(x_btn_row)
        axes_row.addLayout(x_col)

        y_col = QVBoxLayout()
        y_col.addWidget(QLabel("Y Axis"))
        self._y_pos_label = QLabel("0.00")
        self._y_pos_label.setStyleSheet("font-family: monospace; font-size: 16px; color: #f59e0b;")
        y_col.addWidget(self._y_pos_label)
        y_btn_row = QHBoxLayout()
        self._y_minus_btn = QPushButton("▼")
        self._y_minus_btn.clicked.connect(lambda: self._on_jog("y", -1))
        self._y_plus_btn = QPushButton("▲")
        self._y_plus_btn.clicked.connect(lambda: self._on_jog("y", 1))
        y_btn_row.addWidget(self._y_minus_btn)
        y_btn_row.addWidget(self._y_plus_btn)
        y_col.addLayout(y_btn_row)
        axes_row.addLayout(y_col)

        jog_box_layout.addLayout(axes_row)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self._save_btn = QPushButton(_("BTN_SAVE_CONFIG"))
        self._save_btn.clicked.connect(self._on_save_config)
        save_row.addWidget(self._save_btn)
        jog_box_layout.addLayout(save_row)

        settings_layout.addWidget(jog_box)
        settings_layout.addStretch(1)
        self._stack.addWidget(settings_page)

        controller.active_state_changed.connect(self._on_state_changed)

    # --- state sync ---------------------------------------------------------

    def _on_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []

        previously_selected_id = self._current_robot.id if self._current_robot is not None else None
        self._robot_combo.blockSignals(True)
        self._robot_combo.clear()
        for r in robots:
            self._robot_combo.addItem(f"{r.model} (A{r.id})", r.id)
        restore_index = 0
        if previously_selected_id is not None:
            for i in range(self._robot_combo.count()):
                if self._robot_combo.itemData(i) == previously_selected_id:
                    restore_index = i
                    break
        if self._robot_combo.count() > 0:
            self._robot_combo.setCurrentIndex(restore_index)
        self._robot_combo.blockSignals(False)

        self._current_robot = next((r for r in robots if r.id == self._robot_combo.currentData()), None) if robots else None
        self._refresh_controls()

    def _on_robot_combo_changed(self, _index: int) -> None:
        active = self._controller.active_state.active_controller if self._controller.active_state else None
        robots = active.robots if active is not None else []
        robot_id = self._robot_combo.currentData()
        self._current_robot = next((r for r in robots if r.id == robot_id), None)
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        has_robot = self._current_robot is not None
        self._reset_btn.setEnabled(has_robot and self._current_robot.has_xy_table)
        if not has_robot:
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1 if self._current_robot.has_xy_table else 0)
        table = self._current_robot.xy_table

        self._width_spin.blockSignals(True)
        self._length_spin.blockSignals(True)
        size = table["tableSize"] if table else {}
        self._width_spin.setValue(int(size.get("width", _DISPLAY_DEFAULT_SIZE_MM)))
        self._length_spin.setValue(int(size.get("length", _DISPLAY_DEFAULT_SIZE_MM)))
        self._width_spin.blockSignals(False)
        self._length_spin.blockSignals(False)

        pos = table["pos"] if table else {"x": 0, "y": 0}
        self._x_pos_label.setText(f"{float(pos.get('x', 0)):.2f}")
        self._y_pos_label.setText(f"{float(pos.get('y', 0)):.2f}")

    # --- actions --------------------------------------------------------

    def _on_enable(self) -> None:
        if self._current_robot is None:
            return
        # Matches STUDIO's own handleAddTable() exactly: only the flag,
        # no xyTable block yet - see this file's own header for why.
        self._current_robot.set_has_xy_table(True)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_disable(self) -> None:
        if self._current_robot is None:
            return
        self._current_robot.set_has_xy_table(False)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_reset(self) -> None:
        if self._current_robot is None:
            return
        self._current_robot.set_xy_table(_default_xy_table())
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_width_changed(self, value: int) -> None:
        if self._current_robot is None:
            return
        table = self._current_robot.xy_table
        if not table:
            return  # matches STUDIO's own handleSizeChange() no-op guard
        table["tableSize"]["width"] = value
        self._current_robot.set_xy_table(table)
        self._controller.push_active_state()

    def _on_length_changed(self, value: int) -> None:
        if self._current_robot is None:
            return
        table = self._current_robot.xy_table
        if not table:
            return
        table["tableSize"]["length"] = value
        self._current_robot.set_xy_table(table)
        self._controller.push_active_state()

    def _on_step_combo_changed(self, index: int) -> None:
        self._jog_step_mm = self._step_combo.itemData(index)

    def _on_jog(self, axis: str, direction: int) -> None:
        if self._current_robot is None:
            return
        table = self._current_robot.xy_table
        if not table:
            return  # matches STUDIO's own handleJog() no-op guard
        new_value = table["pos"][axis] + direction * self._jog_step_mm
        bound = table["tableSize"]["width" if axis == "x" else "length"]
        new_value = max(0.0, min(new_value, float(bound)))
        table["pos"][axis] = new_value
        self._current_robot.set_xy_table(table)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_save_config(self) -> None:
        if self._current_robot is None:
            return
        table = self._current_robot.xy_table
        if not table:
            return
        safe_name = "".join(c if c.isalnum() else "_" for c in self._current_robot.model)
        path, _filter = QFileDialog.getSaveFileName(self, _("BTN_SAVE_CONFIG"), f"xytable_config_{safe_name}.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(table, f, indent=2)
