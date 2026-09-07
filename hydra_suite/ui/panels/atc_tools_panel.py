# =============================================================================
# HYDRA-UMC SUITE - ui/panels/atc_tools_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own ATCToolsConfig.tsx (465 lines) - the
# Automatic Tool Changer configurator: 3 real layout modes (vertical panel,
# horizontal panel, revolver), a 25-item real URTC tool catalog per slot, a
# real 6-joint + optional table-XY position editor per slot (and for the
# revolver's own base pickup position), JSON export/import of the whole
# config, and a real graphic representation (a grid of tool slots, or a
# circular revolver layout) - built from scratch here with QPainter,
# matching STUDIO's own from-scratch CSS/div graphic 1:1 in structure
# rather than approximated.
#
# NOT built on module_config_panel.py's shared ModuleConfigPanel - STUDIO's
# own `selectedRobot.atc` is a fundamentally different shape than every
# other module (`{enabled, size, ...}`): it's `undefined` when unconfigured
# and a full ATCConfig object otherwise, with no separate `enabled` flag,
# no width/length size, and 3 layout modes instead of one. Forcing that
# shape into ModuleConfigPanel's assumptions would either lose real fields
# or invent ones STUDIO doesn't have - a fresh, purpose-built panel is the
# honest port here, matching [[feedback_no_reference_reuse_dont_invent]]
# in the other direction: this IS a genuinely different design, not a
# spec-less variant of the CNC/Laser/HeatedBed/VacuumTable family.
#
# Deliberately does NOT port ATCToolsConfig.tsx's own right-hand "3D Live
# View" the same way module_config_panel.py's own header explains for the
# CNC/Laser family - same real, separate future work, not part of this
# port. The 2D graphic representation IS ported in full below, since it's
# genuinely from-scratch CSS/divs on the TypeScript side too, not a 3D
# viewport dependency.
#
# Writes via push_active_state() (a full-tree settings mutation), matching
# STUDIO's own updateRobot() - same reasoning as module_config_panel.py's
# own header.
# =============================================================================
from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, RobotView

# STUDIO's own URTC_TOOLS (ATCToolsConfig.tsx) - deliberately NOT run
# through _() translation here either: STUDIO's own source never wraps
# these in t(), they're real tool-catalog names shown identically in
# every UI language on that side too, not an oversight to "fix" here.
URTC_TOOLS: tuple[str, ...] = (
    "None",
    "Soldering Station (T12)",
    "SMT Solder Paste Dispenser",
    "Thermal Paste / Liquid Dispenser",
    "Smart Electric Screwdriver",
    "Vacuum / Pneumatic Gripper",
    "Drill (BL4260)",
    "Gimbal Gripper",
    "NEMA Gripper",
    "AOI (Automated Optical Inspection) System",
    "Engraving Laser Diode (10W optical)",
    "3D Printing Hotend",
    "3D Scanner Probe",
    "SMT Pick & Place Head",
    "Heavy-Duty Electromagnet",
    "Spot Welder Head",
    "Conformal Coating Airbrush",
    "Large-Format Vacuum Gripper",
    "Functional Testing Head",
    "UV Curing Head",
    "Hot Air Rework Nozzle",
    "Pneumatic Press-Fit Inserter",
    "Wire Harnessing / Crimping Actuator",
    "PCB Advanced Inspection",
    "Solder Paste Jetting Valve",
    "Ultrasonic Welder / Packaging Sealer",
)

PANEL_GRIDS: tuple[str, ...] = ("1x1", "1x2", "2x1", "2x2", "2x3", "3x2", "3x3", "3x4", "4x3", "4x4")

JOINT_FIELDS: tuple[str, ...] = ("j1", "j2", "j3", "j4", "j5", "j6")
TABLE_FIELDS: tuple[str, ...] = ("tx", "ty")
JOINT_RANGE_DEG = (-180.0, 180.0)
TABLE_RANGE_MM = (-2000.0, 2000.0)


def _default_pos() -> dict[str, float]:
    return {f: 0.0 for f in JOINT_FIELDS + TABLE_FIELDS}


def _default_atc_config() -> dict[str, Any]:
    return {
        "type": "vertical_panel",
        "panelGrid": "2x2",
        "revolverSlots": 8,
        "tools": [],
    }


class PositionEditor(QWidget):
    """The 6-joint (+ optional table tx/ty) position editor shown inline
    for a revolver's base pickup position or one panel slot - ports
    ATCToolsConfig.tsx's own renderPosEditor() as a reusable widget rather
    than one inline closure per call site."""

    def __init__(self, has_xy_table: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self._spins: dict[str, QSpinBox] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        joints_row = QHBoxLayout()
        for f in JOINT_FIELDS:
            col = QVBoxLayout()
            lbl = QLabel(f"{f.upper()} (°)")
            lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #7f8ea1;")
            col.addWidget(lbl)
            spin = QSpinBox()
            spin.setRange(int(JOINT_RANGE_DEG[0]), int(JOINT_RANGE_DEG[1]))
            spin.setSuffix("°")
            self._spins[f] = spin
            col.addWidget(spin)
            joints_row.addLayout(col)
        layout.addLayout(joints_row)

        if has_xy_table:
            table_row = QHBoxLayout()
            for f in TABLE_FIELDS:
                col = QVBoxLayout()
                lbl = QLabel(f"Table {f[1].upper()} (mm)")
                lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #d97706;")
                col.addWidget(lbl)
                spin = QSpinBox()
                spin.setRange(int(TABLE_RANGE_MM[0]), int(TABLE_RANGE_MM[1]))
                spin.setSuffix(" mm")
                self._spins[f] = spin
                col.addWidget(spin)
                table_row.addLayout(col)
            layout.addLayout(table_row)

    def set_values(self, pos: dict[str, Any]) -> None:
        for f, spin in self._spins.items():
            spin.blockSignals(True)
            spin.setValue(int(pos.get(f, 0) or 0))
            spin.blockSignals(False)

    def connect_field_changed(self, callback) -> None:
        for f, spin in self._spins.items():
            spin.valueChanged.connect(lambda value, field=f: callback(field, float(value)))


class AtcGraphicsWidget(QWidget):
    """Real 2D graphic representation of the current ATC layout - a grid of
    tool slots for panel modes, a circular layout for the revolver - ports
    ATCToolsConfig.tsx's own ATCGraphics() from-scratch CSS/div rendering
    with QPainter instead, same structure (filled vs empty slot per real
    assigned tool, slot number labels)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._config: dict[str, Any] = _default_atc_config()
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_config(self, config: dict[str, Any]) -> None:
        self._config = config
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override signature
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0f172a"))

        atc_type = self._config.get("type", "vertical_panel")
        tools = self._config.get("tools", [])
        tool_by_slot = {t.get("slot"): t.get("tool", "None") for t in tools if isinstance(t, dict)}

        if atc_type in ("vertical_panel", "horizontal_panel"):
            self._paint_panel(painter, tool_by_slot)
        else:
            self._paint_revolver(painter, tool_by_slot)
        painter.end()

    def _paint_panel(self, painter: QPainter, tool_by_slot: dict[int, str]) -> None:
        grid = self._config.get("panelGrid", "2x2")
        try:
            rows, cols = (int(x) for x in grid.split("x"))
        except ValueError:
            rows, cols = 2, 2
        rows, cols = max(rows, 1), max(cols, 1)

        margin = 20
        avail_w, avail_h = self.width() - margin * 2, self.height() - margin * 2
        cell = max(1, min(avail_w // cols, avail_h // rows, 90))
        gap = max(2, cell // 8)
        total_w = cell * cols + gap * (cols - 1)
        total_h = cell * rows + gap * (rows - 1)
        origin_x = (self.width() - total_w) / 2
        origin_y = (self.height() - total_h) / 2

        for i in range(rows * cols):
            r, c = divmod(i, cols)
            x = origin_x + c * (cell + gap)
            y = origin_y + r * (cell + gap)
            has_tool = tool_by_slot.get(i, "None") != "None"
            painter.setPen(QPen(QColor("#0ea5e9" if has_tool else "#334155"), 2, Qt.PenStyle.SolidLine if has_tool else Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor("#082f49" if has_tool else "#0f172a")))
            painter.drawRoundedRect(int(x), int(y), cell, cell, 6, 6)
            painter.setPen(QColor("#64748b"))
            painter.drawText(int(x), int(y) - 4, cell, 14, Qt.AlignmentFlag.AlignLeft, str(i + 1))
            if has_tool:
                dot_r = max(4, cell // 6)
                painter.setBrush(QBrush(QColor("#38bdf8")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(int(x + cell / 2 - dot_r), int(y + cell / 2 - dot_r), dot_r * 2, dot_r * 2)

    def _paint_revolver(self, painter: QPainter, tool_by_slot: dict[int, str]) -> None:
        import math

        slots = max(1, int(self._config.get("revolverSlots", 8) or 8))
        radius = max(70, min(self.width(), self.height()) / 2 - 40)
        cx, cy = self.width() / 2, self.height() / 2

        painter.setPen(QPen(QColor("#334155"), 4))
        painter.setBrush(QBrush(QColor("#1e293b")))
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
        hub_r = max(20, radius * 0.18)
        painter.setBrush(QBrush(QColor("#334155")))
        painter.drawEllipse(int(cx - hub_r), int(cy - hub_r), int(hub_r * 2), int(hub_r * 2))

        for i in range(slots):
            angle = (i / slots) * math.pi * 2 - math.pi / 2
            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius
            has_tool = tool_by_slot.get(i, "None") != "None"
            slot_r = max(14, radius * 0.16)
            painter.setPen(QPen(QColor("#0ea5e9" if has_tool else "#334155"), 2, Qt.PenStyle.SolidLine if has_tool else Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor("#082f49" if has_tool else "#0f172a")))
            painter.drawEllipse(int(x - slot_r), int(y - slot_r), int(slot_r * 2), int(slot_r * 2))
            painter.setPen(QColor("#64748b"))
            painter.drawText(int(x - slot_r), int(y - slot_r - 14), int(slot_r * 2), 12, Qt.AlignmentFlag.AlignCenter, str(i + 1))
            if has_tool:
                dot_r = max(3, slot_r * 0.4)
                painter.setBrush(QBrush(QColor("#38bdf8")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(int(x - dot_r), int(y - dot_r), int(dot_r * 2), int(dot_r * 2))


class AtcToolsPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_robot: RobotView | None = None
        self._editing_slot: int | str | None = None
        self._slot_pos_editors: dict[int, PositionEditor] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        top_row = QHBoxLayout()
        heading = QLabel(_("HEADING_ATC"))
        heading.setObjectName("panelHeading")
        top_row.addWidget(heading)
        top_row.addStretch(1)
        self._reset_btn = QPushButton(_("BTN_RESET_MODULE"))
        self._reset_btn.clicked.connect(self._on_reset)
        top_row.addWidget(self._reset_btn)
        self._load_btn = QPushButton(_("BTN_LOAD_CONFIG"))
        self._load_btn.clicked.connect(self._on_load_config)
        top_row.addWidget(self._load_btn)
        self._save_btn = QPushButton(_("BTN_SAVE_CONFIG"))
        self._save_btn.clicked.connect(self._on_save_config)
        top_row.addWidget(self._save_btn)
        self._robot_combo = QComboBox()
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        top_row.addWidget(self._robot_combo)
        root.addLayout(top_row)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        # Page 0: no ATC configured yet.
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        empty_title = QLabel(_("LBL_NO_MODULE_ASSIGNED", machine="ATC"))
        empty_title.setStyleSheet("font-weight: 600; color: #cfd8e3;")
        empty_layout.addWidget(empty_title)
        empty_desc = QLabel(_("LBL_ATC_EMPTY_DESC"))
        empty_desc.setWordWrap(True)
        empty_desc.setStyleSheet("color: #7f8ea1;")
        empty_layout.addWidget(empty_desc)
        self._enable_btn = QPushButton(_("BTN_ENABLE_MODULE", machine="ATC"))
        self._enable_btn.clicked.connect(self._on_enable)
        empty_layout.addWidget(self._enable_btn)
        empty_layout.addStretch(2)
        self._stack.addWidget(empty_page)

        # Page 1: ATC configured.
        settings_page = QWidget()
        settings_root = QHBoxLayout(settings_page)

        left_col = QScrollArea()
        left_col.setWidgetResizable(True)
        left_inner = QWidget()
        left_layout = QVBoxLayout(left_inner)

        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        self._remove_btn = QPushButton(_("BTN_REMOVE_MODULE"))
        self._remove_btn.setStyleSheet("color: #f43f5e;")
        self._remove_btn.clicked.connect(self._on_disable)
        remove_row.addWidget(self._remove_btn)
        left_layout.addLayout(remove_row)

        type_row = QHBoxLayout()
        self._type_buttons: dict[str, QPushButton] = {}
        for type_key, label_key in (("vertical_panel", "LBL_ATC_VERTICAL"), ("horizontal_panel", "LBL_ATC_HORIZONTAL"), ("revolver", "LBL_ATC_REVOLVER")):
            btn = QPushButton(_(label_key))
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, tk=type_key: self._on_type_changed(tk))
            self._type_buttons[type_key] = btn
            type_row.addWidget(btn)
        left_layout.addLayout(type_row)

        self._panel_group = QGroupBox(_("LBL_PANEL_GRID_LAYOUT"))
        panel_group_layout = QVBoxLayout(self._panel_group)
        self._grid_combo = QComboBox()
        for g in PANEL_GRIDS:
            self._grid_combo.addItem(g, g)
        self._grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        panel_group_layout.addWidget(self._grid_combo)
        left_layout.addWidget(self._panel_group)

        self._revolver_group = QGroupBox(_("LBL_REVOLVER_CAPACITY"))
        revolver_group_layout = QVBoxLayout(self._revolver_group)
        self._revolver_spin = QSpinBox()
        self._revolver_spin.setRange(1, 16)
        self._revolver_spin.valueChanged.connect(self._on_revolver_slots_changed)
        revolver_group_layout.addWidget(self._revolver_spin)
        base_pos_row = QHBoxLayout()
        base_pos_row.addWidget(QLabel(_("LBL_BASE_PICKUP_POS")))
        self._base_pos_toggle = QPushButton(_("BTN_EDIT_POS"))
        self._base_pos_toggle.setCheckable(True)
        self._base_pos_toggle.clicked.connect(self._on_toggle_base_pos)
        base_pos_row.addWidget(self._base_pos_toggle)
        revolver_group_layout.addLayout(base_pos_row)
        self._base_pos_editor: PositionEditor | None = None
        self._base_pos_container = QVBoxLayout()
        revolver_group_layout.addLayout(self._base_pos_container)
        left_layout.addWidget(self._revolver_group)

        left_layout.addWidget(QLabel(_("LBL_TOOL_ASSIGNMENTS")))
        self._slots_container = QVBoxLayout()
        left_layout.addLayout(self._slots_container)
        left_layout.addStretch(1)

        left_inner.setLayout(left_layout)
        left_col.setWidget(left_inner)
        settings_root.addWidget(left_col, 1)

        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_frame)
        self._graphics = AtcGraphicsWidget()
        right_layout.addWidget(self._graphics)
        settings_root.addWidget(right_frame, 1)

        self._stack.addWidget(settings_page)

        controller.active_state_changed.connect(self._on_state_changed)
        self._refresh_controls()

    # --- state sync ----------------------------------------------------

    def _on_state_changed(self, state: HydraState) -> None:
        active = state.active_controller
        robots = active.robots if active is not None else []

        previously_selected_id = self._current_robot.id if self._current_robot else None
        self._robot_combo.blockSignals(True)
        self._robot_combo.clear()
        for r in robots:
            self._robot_combo.addItem(f"{r.id} — {r.model}", r.id)
        restore_index = 0
        if previously_selected_id is not None:
            for i in range(self._robot_combo.count()):
                if self._robot_combo.itemData(i) == previously_selected_id:
                    restore_index = i
                    break
        if robots:
            self._robot_combo.setCurrentIndex(restore_index)
        self._robot_combo.blockSignals(False)

        self._current_robot = robots[restore_index] if robots else None
        self._refresh_controls()

    def _on_robot_combo_changed(self, index: int) -> None:
        active = self._controller.active_state.active_controller if self._controller.active_state else None
        robots = active.robots if active is not None else []
        self._current_robot = robots[index] if 0 <= index < len(robots) else None
        self._editing_slot = None
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        robot = self._current_robot
        has_robot = robot is not None
        config = robot.atc if robot else None

        self._reset_btn.setVisible(bool(config))
        self._load_btn.setEnabled(has_robot)
        self._save_btn.setEnabled(has_robot and bool(config))
        self._robot_combo.setEnabled(has_robot)
        self._enable_btn.setEnabled(has_robot)
        self._stack.setCurrentIndex(1 if config else 0)

        if not config:
            return

        atc_type = config.get("type", "vertical_panel")
        for tk, btn in self._type_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(tk == atc_type)
            btn.blockSignals(False)

        is_panel = atc_type in ("vertical_panel", "horizontal_panel")
        self._panel_group.setVisible(is_panel)
        self._revolver_group.setVisible(not is_panel)

        if is_panel:
            self._grid_combo.blockSignals(True)
            idx = self._grid_combo.findData(config.get("panelGrid", "2x2"))
            self._grid_combo.setCurrentIndex(max(0, idx))
            self._grid_combo.blockSignals(False)
        else:
            self._revolver_spin.blockSignals(True)
            self._revolver_spin.setValue(int(config.get("revolverSlots", 8) or 8))
            self._revolver_spin.blockSignals(False)
            if self._base_pos_editor is not None and self._editing_slot == "revolver":
                self._base_pos_editor.set_values(config.get("revolverPos") or _default_pos())

        self._graphics.set_config(config)
        self._rebuild_slots(config, is_panel)

    def _slot_count(self, config: dict[str, Any]) -> int:
        if config.get("type") in ("vertical_panel", "horizontal_panel"):
            grid = config.get("panelGrid", "2x2")
            try:
                rows, cols = (int(x) for x in grid.split("x"))
            except ValueError:
                rows, cols = 2, 2
            return rows * cols
        return max(1, int(config.get("revolverSlots", 8) or 8))

    def _rebuild_slots(self, config: dict[str, Any], is_panel: bool) -> None:
        while self._slots_container.count():
            item = self._slots_container.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._slot_pos_editors.clear()

        tools_by_slot = {t.get("slot"): t for t in config.get("tools", []) if isinstance(t, dict)}
        slot_count = self._slot_count(config)

        for i in range(slot_count):
            row_widget = QFrame()
            row_widget.setFrameShape(QFrame.Shape.StyledPanel)
            row_layout = QVBoxLayout(row_widget)
            header_row = QHBoxLayout()
            header_row.addWidget(QLabel(str(i + 1)))
            combo = QComboBox()
            for tool in URTC_TOOLS:
                combo.addItem(tool, tool)
            current_tool = tools_by_slot.get(i, {}).get("tool", "None")
            combo.setCurrentIndex(max(0, combo.findData(current_tool)))
            combo.currentIndexChanged.connect(lambda _idx, slot=i, c=combo: self._on_tool_changed(slot, c.currentData()))
            header_row.addWidget(combo, 1)
            if is_panel:
                pos_btn = QPushButton(_("BTN_EDIT_POS"))
                pos_btn.setCheckable(True)
                pos_btn.setChecked(self._editing_slot == i)
                pos_btn.clicked.connect(lambda _checked, slot=i: self._on_toggle_slot_pos(slot))
                header_row.addWidget(pos_btn)
            row_layout.addLayout(header_row)

            if is_panel and self._editing_slot == i:
                editor = PositionEditor(self._current_robot.has_xy_table if self._current_robot else False)
                editor.set_values(tools_by_slot.get(i, {}).get("pos") or _default_pos())
                editor.connect_field_changed(lambda field, value, slot=i: self._on_pos_field_changed(slot, field, value))
                row_layout.addWidget(editor)
                self._slot_pos_editors[i] = editor

            self._slots_container.addWidget(row_widget)

    # --- writes ----------------------------------------------------------

    def _push(self) -> None:
        self._controller.push_active_state()

    def _update_config(self, updates: dict[str, Any]) -> None:
        if self._current_robot is None:
            return
        config = dict(self._current_robot.atc or _default_atc_config())
        config.update(updates)
        self._current_robot.set_atc(config)
        self._refresh_controls()
        self._push()

    def _on_enable(self) -> None:
        if self._current_robot is None:
            return
        self._current_robot.set_atc(_default_atc_config())
        self._refresh_controls()
        self._push()

    def _on_disable(self) -> None:
        if self._current_robot is None:
            return
        self._current_robot.set_atc(None)
        self._editing_slot = None
        self._refresh_controls()
        self._push()

    def _on_reset(self) -> None:
        if self._current_robot is None:
            return
        self._current_robot.set_atc(_default_atc_config())
        self._editing_slot = None
        self._refresh_controls()
        self._push()

    def _on_type_changed(self, type_key: str) -> None:
        self._update_config({"type": type_key})

    def _on_grid_changed(self, _index: int) -> None:
        grid = self._grid_combo.currentData()
        if grid is None:
            return
        self._update_config({"panelGrid": grid, "tools": []})

    def _on_revolver_slots_changed(self, value: int) -> None:
        self._update_config({"revolverSlots": value, "tools": []})

    def _on_tool_changed(self, slot: int, tool: str) -> None:
        if self._current_robot is None or tool is None:
            return
        config = dict(self._current_robot.atc or _default_atc_config())
        tools = [dict(t) for t in config.get("tools", [])]
        idx = next((i for i, t in enumerate(tools) if t.get("slot") == slot), None)
        if idx is not None:
            tools[idx]["tool"] = tool
        else:
            tools.append({"slot": slot, "tool": tool, "pos": _default_pos()})
        self._update_config({"tools": tools})

    def _on_pos_field_changed(self, slot: int | str, field: str, value: float) -> None:
        if self._current_robot is None:
            return
        config = dict(self._current_robot.atc or _default_atc_config())
        if slot == "revolver":
            pos = dict(config.get("revolverPos") or _default_pos())
            pos[field] = value
            self._update_config({"revolverPos": pos})
            return
        tools = [dict(t) for t in config.get("tools", [])]
        idx = next((i for i, t in enumerate(tools) if t.get("slot") == slot), None)
        if idx is None:
            tools.append({"slot": slot, "tool": "None", "pos": _default_pos()})
            idx = len(tools) - 1
        pos = dict(tools[idx].get("pos") or _default_pos())
        pos[field] = value
        tools[idx]["pos"] = pos
        self._update_config({"tools": tools})

    def _on_toggle_slot_pos(self, slot: int) -> None:
        self._editing_slot = None if self._editing_slot == slot else slot
        self._refresh_controls()

    def _on_toggle_base_pos(self) -> None:
        self._editing_slot = None if self._editing_slot == "revolver" else "revolver"
        if self._editing_slot == "revolver":
            while self._base_pos_container.count():
                item = self._base_pos_container.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
            self._base_pos_editor = PositionEditor(self._current_robot.has_xy_table if self._current_robot else False)
            config = self._current_robot.atc if self._current_robot else None
            self._base_pos_editor.set_values((config or {}).get("revolverPos") or _default_pos())
            self._base_pos_editor.connect_field_changed(lambda field, value: self._on_pos_field_changed("revolver", field, value))
            self._base_pos_container.addWidget(self._base_pos_editor)
        else:
            while self._base_pos_container.count():
                item = self._base_pos_container.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
            self._base_pos_editor = None
        self._base_pos_toggle.setChecked(self._editing_slot == "revolver")

    # --- JSON import/export ----------------------------------------------

    def _on_save_config(self) -> None:
        if self._current_robot is None:
            return
        config = self._current_robot.atc
        if not config:
            return
        safe_name = "".join(c if c.isalnum() else "_" for c in self._current_robot.model)
        path, _filter = QFileDialog.getSaveFileName(self, _("BTN_SAVE_CONFIG"), f"atc_config_{safe_name}.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _on_load_config(self) -> None:
        if self._current_robot is None:
            return
        path, _filter = QFileDialog.getOpenFileName(self, _("BTN_LOAD_CONFIG"), "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, _("BTN_LOAD_CONFIG"), str(exc))
            return
        if not isinstance(data, dict) or "type" not in data:
            QMessageBox.warning(self, _("BTN_LOAD_CONFIG"), _("MSG_ATC_INVALID_CONFIG"))
            return
        self._editing_slot = None
        self._update_config(data)
