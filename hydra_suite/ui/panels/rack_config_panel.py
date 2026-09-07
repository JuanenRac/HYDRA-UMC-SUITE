# =============================================================================
# HYDRA-UMC SUITE - ui/panels/rack_config_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own RackConfigView.tsx (228 lines) - the
# 7th of 11 panels from [[project_suite_studio_parity_gap]]. NOT built on
# module_config_panel.py's shared ModuleConfigPanel: `rackSystem` nests TWO
# real sub-racks (rack1/rack2, each its own type/capacity/usableSlots/
# basePickupPos), a shape none of that family's single-module panels have.
# `rackSystem` itself is never undefined on the TypeScript side (unlike
# `atc`/`xyTable`) - `createDefaultRobots()` always seeds a real one and
# `enabled` alone gates whether it's in use, closer to the
# ModuleConfigPanel family's `{enabled, ...}` shape in that one respect,
# but the nested rack1/rack2 pair still doesn't fit that base class.
#
# Faithfully reproduces a real, easy-to-miss quirk in STUDIO's own source
# rather than "fixing" it here: each rack's own Reset button
# (`handleReset()`, defined inside `renderRack(rackId, title)`) does NOT
# reference `rackId` at all - clicking Reset on EITHER rack1 or rack2
# resets BOTH racks to their real defaults (and force-sets `enabled: true`
# even if it was already true). See _on_reset() below.
#
# Deliberately does NOT port a live 3D preview - RackConfigView.tsx itself
# has none either (no <Canvas> anywhere in that file), unlike the
# CNC/Laser/HeatedBed/VacuumTable/XYTable family - nothing omitted here.
#
# Writes via push_active_state(), matching STUDIO's own updateRobot().
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import RACK_MAX_CAPACITY, HydraState, RobotView, default_rack_system

RACK_TYPES: tuple[str, ...] = ("None", "Input", "Output")
SLOT_GRID_COLUMNS = 6
POS_FIELDS: tuple[str, ...] = ("j1", "j2", "j3", "j4", "j5", "j6")
TABLE_FIELDS: tuple[str, ...] = ("tx", "ty")


class RackGroupWidget(QGroupBox):
    def __init__(self, rack_id: str, title: str, on_field_changed, on_slot_toggle, parent: QWidget | None = None):
        super().__init__(title, parent)
        self._rack_id = rack_id
        self._on_field_changed = on_field_changed
        self._on_slot_toggle = on_slot_toggle
        self._slot_buttons: list[QPushButton] = []
        self._pos_spins: dict[str, QDoubleSpinBox] = {}

        layout = QVBoxLayout(self)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel(_("LBL_RACK_TYPE")))
        self._type_combo = QComboBox()
        self._type_combo.addItem(_("LBL_DISABLED"), "None")
        self._type_combo.addItem(_("LBL_INPUT_RACK"), "Input")
        self._type_combo.addItem(_("LBL_OUTPUT_RACK"), "Output")
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self._type_combo, 1)
        layout.addLayout(type_row)

        self._body = QWidget()
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        cap_row = QHBoxLayout()
        cap_row.addWidget(QLabel(_("LBL_CAPACITY")))
        self._capacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._capacity_slider.setRange(1, RACK_MAX_CAPACITY)
        self._capacity_slider.valueChanged.connect(self._on_capacity_changed)
        cap_row.addWidget(self._capacity_slider, 1)
        self._capacity_label = QLabel("24")
        self._capacity_label.setStyleSheet("font-family: monospace; color: #38bdf8;")
        cap_row.addWidget(self._capacity_label)
        body_layout.addLayout(cap_row)

        body_layout.addWidget(QLabel(_("LBL_USABLE_SLOTS")))
        self._slots_grid = QGridLayout()
        slots_host = QWidget()
        slots_host.setLayout(self._slots_grid)
        body_layout.addWidget(slots_host)

        body_layout.addWidget(QLabel(_("LBL_BASE_PICKUP_POS")))
        pos_grid = QGridLayout()
        for i, joint in enumerate(POS_FIELDS):
            col = QVBoxLayout()
            col.addWidget(QLabel(f"{joint.upper()} (°)"))
            spin = QDoubleSpinBox()
            spin.setRange(-360.0, 360.0)
            spin.setDecimals(2)
            spin.valueChanged.connect(lambda value, f=joint: self._on_pos_changed(f, value))
            self._pos_spins[joint] = spin
            col.addWidget(spin)
            pos_grid.addLayout(col, i // 3, i % 3)
        body_layout.addLayout(pos_grid)

        self._table_row = QWidget()
        table_row_layout = QHBoxLayout(self._table_row)
        table_row_layout.setContentsMargins(0, 4, 0, 0)
        for field in TABLE_FIELDS:
            col = QVBoxLayout()
            label = QLabel(f"Table {field[1:].upper()} (mm)")
            label.setStyleSheet("color: #d97706;")
            col.addWidget(label)
            spin = QDoubleSpinBox()
            spin.setRange(-5000.0, 5000.0)
            spin.setDecimals(2)
            spin.valueChanged.connect(lambda value, f=field: self._on_pos_changed(f, value))
            self._pos_spins[field] = spin
            col.addWidget(spin)
            table_row_layout.addLayout(col)
        body_layout.addWidget(self._table_row)

        layout.addWidget(self._body)

    def refresh(self, rack: dict, has_xy_table: bool) -> None:
        self._type_combo.blockSignals(True)
        idx = self._type_combo.findData(rack.get("type", "None"))
        self._type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._type_combo.blockSignals(False)

        is_active = rack.get("type", "None") != "None"
        self._body.setVisible(is_active)
        if not is_active:
            return

        capacity = int(rack.get("capacity", RACK_MAX_CAPACITY))
        self._capacity_slider.blockSignals(True)
        self._capacity_slider.setValue(capacity)
        self._capacity_slider.blockSignals(False)
        self._capacity_label.setText(str(capacity))

        usable_slots = rack.get("usableSlots", [])
        for btn in self._slot_buttons:
            self._slots_grid.removeWidget(btn)
            btn.deleteLater()
        self._slot_buttons = []
        for i in range(capacity):
            usable = bool(usable_slots[i]) if i < len(usable_slots) else False
            btn = QPushButton(f"{i + 1}\n{'☑' if usable else '☐'}")
            btn.setCheckable(True)
            btn.setChecked(usable)
            btn.clicked.connect(lambda _checked=False, index=i: self._on_slot_toggle(self._rack_id, index))
            self._slots_grid.addWidget(btn, i // SLOT_GRID_COLUMNS, i % SLOT_GRID_COLUMNS)
            self._slot_buttons.append(btn)

        pos = rack.get("basePickupPos", {})
        for field, spin in self._pos_spins.items():
            spin.blockSignals(True)
            spin.setValue(float(pos.get(field, 0)))
            spin.blockSignals(False)
        self._table_row.setVisible(has_xy_table)

    def _on_type_changed(self, index: int) -> None:
        self._on_field_changed(self._rack_id, "type", self._type_combo.itemData(index))

    def _on_capacity_changed(self, value: int) -> None:
        self._capacity_label.setText(str(value))
        self._on_field_changed(self._rack_id, "capacity", value)

    def _on_pos_changed(self, field: str, value: float) -> None:
        self._on_field_changed(self._rack_id, f"basePickupPos.{field}", value)


class RackConfigPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_robot: RobotView | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        top_row = QHBoxLayout()
        heading = QLabel(_("HEADING_RACK_MANAGER"))
        heading.setObjectName("panelHeading")
        top_row.addWidget(heading)
        top_row.addStretch(1)
        self._robot_combo = QComboBox()
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        top_row.addWidget(self._robot_combo)
        outer.addLayout(top_row)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack, 1)

        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        empty_title = QLabel(_("LBL_NO_MODULE_ASSIGNED", machine="Rack"))
        empty_title.setStyleSheet("font-weight: 600; color: #cfd8e3;")
        empty_layout.addWidget(empty_title)
        empty_desc = QLabel(_("LBL_NO_MODULE_DESC"))
        empty_desc.setWordWrap(True)
        empty_desc.setStyleSheet("color: #7f8ea1;")
        empty_layout.addWidget(empty_desc)
        self._enable_btn = QPushButton(_("BTN_ENABLE_MODULE", machine="Rack"))
        self._enable_btn.clicked.connect(self._on_enable)
        empty_layout.addWidget(self._enable_btn)
        empty_layout.addStretch(2)
        self._stack.addWidget(empty_page)

        settings_page = QWidget()
        settings_outer = QVBoxLayout(settings_page)
        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        self._remove_btn = QPushButton(_("BTN_REMOVE_MODULE"))
        self._remove_btn.setStyleSheet("color: #f43f5e;")
        self._remove_btn.clicked.connect(self._on_disable)
        remove_row.addWidget(self._remove_btn)
        settings_outer.addLayout(remove_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        racks_host = QWidget()
        racks_layout = QHBoxLayout(racks_host)
        self._rack1_widget = RackGroupWidget("rack1", _("LBL_RACK1"), self._on_field_changed, self._on_slot_toggle)
        self._rack2_widget = RackGroupWidget("rack2", _("LBL_RACK2"), self._on_field_changed, self._on_slot_toggle)
        reset_row1 = QVBoxLayout()
        reset_btn1 = QPushButton(_("BTN_RESET_MODULE"))
        reset_btn1.clicked.connect(self._on_reset)
        reset_row1.addWidget(reset_btn1)
        reset_row1.addWidget(self._rack1_widget)
        reset_row2 = QVBoxLayout()
        reset_btn2 = QPushButton(_("BTN_RESET_MODULE"))
        reset_btn2.clicked.connect(self._on_reset)
        reset_row2.addWidget(reset_btn2)
        reset_row2.addWidget(self._rack2_widget)
        racks_layout.addLayout(reset_row1)
        racks_layout.addLayout(reset_row2)
        scroll.setWidget(racks_host)
        settings_outer.addWidget(scroll, 1)
        self._stack.addWidget(settings_page)

        controller.active_state_changed.connect(self._on_state_changed)

    # --- state sync ----------------------------------------------------

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
        if self._current_robot is None:
            self._stack.setCurrentIndex(0)
            return
        config = self._current_robot.rack_system
        self._stack.setCurrentIndex(1 if config.get("enabled") else 0)
        if not config.get("enabled"):
            return
        has_xy_table = self._current_robot.has_xy_table
        self._rack1_widget.refresh(config["rack1"], has_xy_table)
        self._rack2_widget.refresh(config["rack2"], has_xy_table)

    # --- actions ---------------------------------------------------------

    def _on_enable(self) -> None:
        if self._current_robot is None:
            return
        config = self._current_robot.rack_system
        config["enabled"] = True
        self._current_robot.set_rack_system(config)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_disable(self) -> None:
        if self._current_robot is None:
            return
        config = self._current_robot.rack_system
        config["enabled"] = False
        self._current_robot.set_rack_system(config)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_reset(self) -> None:
        # Matches STUDIO's own handleReset() exactly: BOTH racks reset,
        # regardless of which rack's own Reset button was clicked - see
        # this file's own header for why this is intentional, not a bug
        # introduced here.
        if self._current_robot is None:
            return
        config = default_rack_system()
        config["enabled"] = True
        self._current_robot.set_rack_system(config)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_field_changed(self, rack_id: str, field: str, value) -> None:
        if self._current_robot is None:
            return
        config = self._current_robot.rack_system
        rack = config[rack_id]
        if field.startswith("basePickupPos."):
            _, joint = field.split(".", 1)
            rack["basePickupPos"][joint] = value
        else:
            rack[field] = value
        self._current_robot.set_rack_system(config)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_slot_toggle(self, rack_id: str, index: int) -> None:
        if self._current_robot is None:
            return
        config = self._current_robot.rack_system
        rack = config[rack_id]
        slots = list(rack.get("usableSlots", []))
        while len(slots) <= index:
            slots.append(False)
        slots[index] = not slots[index]
        rack["usableSlots"] = slots
        self._current_robot.set_rack_system(config)
        self._controller.push_active_state()
        self._refresh_controls()
