# =============================================================================
# HYDRA-UMC SUITE - ui/panels/pick_and_place_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own PickAndPlace.tsx (205 lines) - the
# 8th of 11 panels from [[project_suite_studio_parity_gap]]. NOT built
# directly on ModuleConfigPanel: unlike CNC/Laser (one module key per
# panel instance), this ONE panel switches between TWO real module keys
# (`juanenPnP`/`lumenPnP`) via its own in-panel Machine combo - reuses
# `RobotView.module()`/`module_enabled()`/`set_module()`'s existing
# generic accessors directly rather than instantiating ModuleConfigPanel
# twice, since the machine-type switch itself needs to live above/outside
# that base class's own single-module assumption.
#
# STUDIO's own `isPnpMachine = machineType === 'juanenPnP' || machineType
# === 'lumenPnP'` is ALWAYS true given the Machine combo only ever offers
# those two values - the `else` branch (plain width/length, same shape as
# CNC/Laser) is real but unreachable through this panel's own UI. Ported
# faithfully anyway (not collapsed away) in case a 3rd machine type is
# ever added to the combo on either side - same "reproduce, don't
# simplify" discipline as every other panel in this family.
#
# The 5 pose-preview sliders (axisX/axisY/axisZ/nozzle1Rotation/
# nozzle2Rotation) use STUDIO's own REAL fixed hardware bounds (433mm/
# 487mm/90mm travel, +-180 deg nozzle rotation) - not placeholder round
# numbers. Manual pose preview only: neither side has a live firmware
# feed for either PnP machine yet (see PickAndPlace.tsx's own comment).
#
# Also ports the right-hand "3D Live View" for real - a dedicated
# RobotViewport (render/viewport.py) switched into PnP module-only mode
# (set_attached_pnp(), render/pnp_rig.py) rather than module_rig.py's
# primitive-built family: juanenPnP/lumenPnP have a real STL rig
# (assets/meshes/lumenpnp/), the one real-mesh exception among all the
# tool-attachment modules - see module_config_panel.py's own header for
# the 4 primitive ones.
#
# Writes via push_active_state(), matching STUDIO's own updateRobot().
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, RobotView
from hydra_suite.render.viewport import RobotViewport

MACHINE_TYPES: tuple[str, ...] = ("juanenPnP", "lumenPnP")
MACHINE_LABELS: dict[str, str] = {"juanenPnP": "JuanenPnP", "lumenPnP": "LumenPnP"}

# (field, label key, min, max) - real fixed hardware bounds, matching
# PickAndPlace.tsx's own literal values exactly.
PNP_AXES: tuple[tuple[str, str, int, int], ...] = (
    ("axisX", "LBL_PNP_AXIS_X", 0, 433),
    ("axisY", "LBL_PNP_AXIS_Y", 0, 487),
    ("axisZ", "LBL_PNP_AXIS_Z", 0, 90),
    ("nozzle1Rotation", "LBL_PNP_NOZZLE1", -180, 180),
    ("nozzle2Rotation", "LBL_PNP_NOZZLE2", -180, 180),
)


class PickAndPlacePanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_robot: RobotView | None = None
        self._machine_type: str = "juanenPnP"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        top_row = QHBoxLayout()
        heading = QLabel(_("HEADING_PICK_AND_PLACE"))
        heading.setObjectName("panelHeading")
        top_row.addWidget(heading)
        top_row.addStretch(1)

        self._machine_combo = QComboBox()
        for key in MACHINE_TYPES:
            self._machine_combo.addItem(f"{_('LBL_MACHINE')}: {MACHINE_LABELS[key]}", key)
        self._machine_combo.currentIndexChanged.connect(self._on_machine_combo_changed)
        top_row.addWidget(self._machine_combo)

        self._reset_btn = QPushButton(_("BTN_RESET_MODULE"))
        self._reset_btn.clicked.connect(self._on_reset)
        top_row.addWidget(self._reset_btn)

        self._robot_combo = QComboBox()
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        top_row.addWidget(self._robot_combo)
        outer.addLayout(top_row)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack, 1)

        self._empty_title = QLabel()
        self._empty_title.setStyleSheet("font-weight: 600; color: #cfd8e3;")
        self._enable_btn = QPushButton()
        self._enable_btn.clicked.connect(self._on_enable)
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        empty_layout.addWidget(self._empty_title)
        empty_desc = QLabel(_("LBL_NO_MODULE_DESC"))
        empty_desc.setWordWrap(True)
        empty_desc.setStyleSheet("color: #7f8ea1;")
        empty_layout.addWidget(empty_desc)
        empty_layout.addWidget(self._enable_btn)
        empty_layout.addStretch(2)
        self._stack.addWidget(empty_page)

        # Settings form + live 3D preview, side by side - matches STUDIO's
        # own PickAndPlace.tsx two-column layout (settings form on the
        # left, its own <Canvas> on the right), same pattern
        # module_config_panel.py's own settings_page now uses too.
        settings_page = QWidget()
        settings_page_layout = QHBoxLayout(settings_page)
        settings_page_layout.setContentsMargins(0, 0, 0, 0)
        settings_page_layout.setSpacing(8)

        settings_column = QWidget()
        settings_layout = QVBoxLayout(settings_column)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_box = QGroupBox(_("GROUP_MODULE_SETTINGS"))
        settings_box_layout = QVBoxLayout(settings_box)

        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        self._remove_btn = QPushButton(_("BTN_REMOVE_MODULE"))
        self._remove_btn.setStyleSheet("color: #f43f5e;")
        self._remove_btn.clicked.connect(self._on_disable)
        remove_row.addWidget(self._remove_btn)
        settings_box_layout.addLayout(remove_row)

        # PnP pose-preview page (always shown in practice - see this
        # file's own header for why the size-only branch below is real
        # but currently unreachable).
        self._pnp_page = QWidget()
        pnp_layout = QVBoxLayout(self._pnp_page)
        pnp_layout.setContentsMargins(0, 0, 0, 0)
        pnp_hint = QLabel(_("LBL_PNP_POSE_PREVIEW"))
        pnp_hint.setStyleSheet("color: #7f8ea1; font-size: 10px; text-transform: uppercase;")
        pnp_layout.addWidget(pnp_hint)
        self._axis_sliders: dict[str, QSlider] = {}
        self._axis_spins: dict[str, QSpinBox] = {}
        for field, label_key, lo, hi in PNP_AXES:
            row = QHBoxLayout()
            row.addWidget(QLabel(_(label_key)))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            spin = QSpinBox()
            spin.setRange(lo, hi)
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            slider.valueChanged.connect(lambda value, f=field: self._on_axis_changed(f, value))
            self._axis_sliders[field] = slider
            self._axis_spins[field] = spin
            row.addWidget(slider, 1)
            row.addWidget(spin)
            pnp_layout.addLayout(row)
        settings_box_layout.addWidget(self._pnp_page)

        # Size-only page - same shape as CNC/Laser, real in STUDIO's own
        # source but not reachable via this panel's current Machine combo.
        self._size_page = QWidget()
        size_layout = QHBoxLayout(self._size_page)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.addWidget(QLabel(_("LBL_WIDTH_X")))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(10, 5000)
        self._width_spin.setSuffix(" mm")
        self._width_spin.valueChanged.connect(self._on_width_changed)
        size_layout.addWidget(self._width_spin)
        size_layout.addWidget(QLabel(_("LBL_LENGTH_Y")))
        self._length_spin = QSpinBox()
        self._length_spin.setRange(10, 5000)
        self._length_spin.setSuffix(" mm")
        self._length_spin.valueChanged.connect(self._on_length_changed)
        size_layout.addWidget(self._length_spin)
        settings_box_layout.addWidget(self._size_page)

        settings_layout.addWidget(settings_box)
        settings_layout.addStretch(1)
        settings_page_layout.addWidget(settings_column, 1)

        self._pnp_viewport = RobotViewport()
        self._pnp_viewport.setMinimumWidth(220)
        settings_page_layout.addWidget(self._pnp_viewport, 1)

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

    def _on_machine_combo_changed(self, index: int) -> None:
        self._machine_type = self._machine_combo.itemData(index)
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        has_robot = self._current_robot is not None
        self._reset_btn.setEnabled(has_robot and self._current_robot.module_enabled(self._machine_type))
        machine_label = MACHINE_LABELS[self._machine_type]
        self._empty_title.setText(_("LBL_NO_MODULE_ASSIGNED", machine=machine_label))
        self._enable_btn.setText(_("BTN_ENABLE_MODULE", machine=machine_label))
        if not has_robot:
            self._stack.setCurrentIndex(0)
            self._pnp_viewport.set_attached_pnp(None)
            return

        enabled = self._current_robot.module_enabled(self._machine_type)
        self._stack.setCurrentIndex(1 if enabled else 0)
        if not enabled:
            self._pnp_viewport.set_attached_pnp(None)
            return

        module = self._current_robot.module(self._machine_type)
        is_pnp = self._machine_type in ("juanenPnP", "lumenPnP")
        self._pnp_page.setVisible(is_pnp)
        self._size_page.setVisible(not is_pnp)

        if is_pnp:
            for field, _label_key, _lo, _hi in PNP_AXES:
                value = int(module.get(field, 0) or 0)
                self._axis_sliders[field].blockSignals(True)
                self._axis_spins[field].blockSignals(True)
                self._axis_sliders[field].setValue(value)
                self._axis_spins[field].setValue(value)
                self._axis_sliders[field].blockSignals(False)
                self._axis_spins[field].blockSignals(False)
            self._pnp_viewport.set_attached_pnp(
                self._machine_type,
                axis_x_mm=float(module.get("axisX", 0) or 0),
                axis_y_mm=float(module.get("axisY", 0) or 0),
                axis_z_mm=float(module.get("axisZ", 0) or 0),
                nozzle1_deg=float(module.get("nozzle1Rotation", 0) or 0),
                nozzle2_deg=float(module.get("nozzle2Rotation", 0) or 0),
            )
        else:
            # Real in STUDIO's own source but unreachable through this
            # panel's Machine combo (see this file's own header) - no real
            # PnP geometry applies to a hypothetical non-PnP machine type,
            # so the preview stays detached rather than showing stale
            # LumenPnP geometry.
            self._pnp_viewport.set_attached_pnp(None)
            size = module.get("size", {})
            self._width_spin.blockSignals(True)
            self._length_spin.blockSignals(True)
            self._width_spin.setValue(int(size.get("width", 500)))
            self._length_spin.setValue(int(size.get("length", 500)))
            self._width_spin.blockSignals(False)
            self._length_spin.blockSignals(False)

    # --- actions ---------------------------------------------------------

    def _on_enable(self) -> None:
        if self._current_robot is None:
            return
        module = self._current_robot.module(self._machine_type)
        module["enabled"] = True
        self._current_robot.set_module(self._machine_type, module)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_disable(self) -> None:
        if self._current_robot is None:
            return
        module = self._current_robot.module(self._machine_type)
        module["enabled"] = False
        self._current_robot.set_module(self._machine_type, module)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_reset(self) -> None:
        if self._current_robot is None:
            return
        is_pnp = self._machine_type in ("juanenPnP", "lumenPnP")
        module = {
            "enabled": True,
            "size": {"width": 500, "length": 500},
            "worldPos": {"x": 0, "y": 0},
            "worldRot": 0,
            "renderScale": 1,
        }
        if is_pnp:
            module.update({"axisX": 0, "axisY": 0, "axisZ": 0, "nozzle1Rotation": 0, "nozzle2Rotation": 0})
        self._current_robot.set_module(self._machine_type, module)
        self._controller.push_active_state()
        self._refresh_controls()

    def _on_axis_changed(self, field: str, value: int) -> None:
        if self._current_robot is None:
            return
        module = self._current_robot.module(self._machine_type)
        module[field] = value
        self._current_robot.set_module(self._machine_type, module)
        # Updates the live 3D preview immediately rather than waiting for
        # the next state broadcast to round-trip back from the server -
        # same real gap fixed in module_config_panel.py's own
        # _on_size_changed(), matching STUDIO's own reactive <Canvas>.
        self._refresh_controls()
        self._controller.push_active_state()

    def _on_width_changed(self, value: int) -> None:
        if self._current_robot is None:
            return
        module = self._current_robot.module(self._machine_type)
        module.setdefault("size", {})["width"] = value
        self._current_robot.set_module(self._machine_type, module)
        self._controller.push_active_state()

    def _on_length_changed(self, value: int) -> None:
        if self._current_robot is None:
            return
        module = self._current_robot.module(self._machine_type)
        module.setdefault("size", {})["length"] = value
        self._current_robot.set_module(self._machine_type, module)
        self._controller.push_active_state()
