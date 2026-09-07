# =============================================================================
# HYDRA-UMC SUITE - ui/panels/kinematic_brain_stage_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real port of HYDRA-UMC-STUDIO's own KinematicBrainStage.tsx (316 lines) -
# the 9th of 11 panels from [[project_suite_studio_parity_gap]]. Control
# panel for the Kinematic Brain's OWN local 6-axis stage (STM32H745 -
# HYDRA-UMC's docs/PINOUT_STM32H745_KINEMATIC_BRAIN.TXT section 3,
# docs/CANBUS_STM32H745.TXT section 4). CONFIRMED job per axis: X/Y1/Y2 =
# dual-Y XY gantry table, Z = table/head height, E0 = ATC revolver/turret
# index (rotary), E1 = future conveyor belt (wired, not yet installed).
#
# UNLIKE every panel in this family so far: this is CONTROLLER-level state
# (`ControllerView.kinematic_brain_stage`), not per-robot - there is
# exactly one Kinematic Brain per controller, so this panel has no robot
# selector at all.
#
# Talks to the real hardware the same way STUDIO's own source does today:
# nothing yet - this is a live UI over local/synced state, same
# "usable/demoable ahead of real hardware" status as the rest of this
# dashboard. Wiring this to the real SPI1 link is a real follow-up, not
# done here - matches that file's own header exactly.
#
# Writes via push_active_state(), matching STUDIO's own updateController().
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import ControllerView, HydraState

AXIS_KEYS: tuple[str, ...] = ("x", "y1", "y2", "z")
JOG_STEPS_MM: tuple[float, ...] = (0.01, 0.1, 1.0, 2.0, 5.0, 10.0, 100.0)

# (endstop key, label) - matches KinematicBrainStage.tsx's own endstopEntries exactly.
ENDSTOP_ENTRIES: tuple[tuple[str, str], ...] = (
    ("xMin", "X MIN"), ("xMax", "X MAX"),
    ("y1Min", "Y1 MIN"), ("y1Max", "Y1 MAX"),
    ("y2Min", "Y2 MIN"), ("y2Max", "Y2 MAX"),
    ("zMin", "Z MIN"), ("zMax", "Z MAX"),
    ("e0Min", "E0 MIN"), ("e0Max", "E0 MAX"),
    ("e1Min", "E1 MIN"), ("e1Max", "E1 MAX"),
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class KinematicBrainStagePanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._active_controller: ControllerView | None = None
        self._jog_step_mm: float = 10.0

        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        outer_scroll.setWidget(host)
        page_layout.addWidget(outer_scroll)

        heading = QLabel(_("HEADING_KINEMATIC_BRAIN_STAGE"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        # --- XY Gantry + Z --------------------------------------------------
        gantry_box = QGroupBox(_("LBL_GANTRY"))
        gantry_layout = QVBoxLayout(gantry_box)

        step_row = QHBoxLayout()
        step_row.addWidget(QLabel(_("LBL_STEP")))
        self._step_combo = QComboBox()
        for step in JOG_STEPS_MM:
            self._step_combo.addItem(f"{step:g} mm", step)
        self._step_combo.setCurrentIndex(JOG_STEPS_MM.index(10.0))
        self._step_combo.currentIndexChanged.connect(self._on_step_combo_changed)
        step_row.addWidget(self._step_combo)
        step_row.addStretch(1)
        gantry_layout.addLayout(step_row)

        axes_row = QHBoxLayout()
        self._axis_labels: dict[str, QLabel] = {}
        for axis in AXIS_KEYS:
            col = QVBoxLayout()
            col.addWidget(QLabel(axis.upper()))
            value_label = QLabel("0.00")
            value_label.setStyleSheet("font-family: monospace; font-size: 16px; color: #f59e0b;")
            self._axis_labels[axis] = value_label
            col.addWidget(value_label)
            btn_row = QHBoxLayout()
            minus = QPushButton("−")
            minus.clicked.connect(lambda _c=False, a=axis: self._on_jog(a, -1))
            plus = QPushButton("+")
            plus.clicked.connect(lambda _c=False, a=axis: self._on_jog(a, 1))
            btn_row.addWidget(minus)
            btn_row.addWidget(plus)
            col.addLayout(btn_row)
            axes_row.addLayout(col)
        gantry_layout.addLayout(axes_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel(_("LBL_WIDTH_X")))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(100, 5000)
        self._width_spin.valueChanged.connect(lambda v: self._on_table_size_changed("width", v, 100, 5000))
        size_row.addWidget(self._width_spin)
        size_row.addWidget(QLabel(_("LBL_LENGTH_Y")))
        self._length_spin = QSpinBox()
        self._length_spin.setRange(100, 5000)
        self._length_spin.valueChanged.connect(lambda v: self._on_table_size_changed("length", v, 100, 5000))
        size_row.addWidget(self._length_spin)
        size_row.addWidget(QLabel(_("LBL_HEIGHT_Z")))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(10, 1000)
        self._height_spin.valueChanged.connect(lambda v: self._on_table_size_changed("height", v, 10, 1000))
        size_row.addWidget(self._height_spin)
        gantry_layout.addLayout(size_row)
        layout.addWidget(gantry_box)

        row2 = QHBoxLayout()

        # --- Heated Bed -------------------------------------------------
        bed_box = QGroupBox(_("HEADING_HEATED_BED"))
        bed_layout = QVBoxLayout(bed_box)
        self._therm1_label = QLabel("24.0°C")
        self._therm2_label = QLabel("24.0°C")
        for label_key, value_label in ((_("LBL_THERMISTOR_1"), self._therm1_label), (_("LBL_THERMISTOR_2"), self._therm2_label)):
            row = QHBoxLayout()
            row.addWidget(QLabel(label_key))
            row.addStretch(1)
            row.addWidget(value_label)
            bed_layout.addLayout(row)
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel(_("LBL_TARGET_TEMP")))
        self._target_temp_spin = QSpinBox()
        self._target_temp_spin.setRange(0, 150)
        self._target_temp_spin.valueChanged.connect(self._on_target_temp_changed)
        target_row.addWidget(self._target_temp_spin)
        self._ssr_btn = QPushButton()
        self._ssr_btn.clicked.connect(self._on_ssr_toggle)
        target_row.addWidget(self._ssr_btn)
        bed_layout.addLayout(target_row)
        row2.addWidget(bed_box)

        # --- ATC Revolver -------------------------------------------------
        atc_box = QGroupBox(_("LBL_ATC_REVOLVER_E0"))
        atc_layout = QVBoxLayout(atc_box)
        step_row2 = QHBoxLayout()
        prev_btn = QPushButton("◀")
        prev_btn.clicked.connect(lambda: self._on_atc_step(-1))
        step_row2.addWidget(prev_btn)
        self._atc_index_label = QLabel("1")
        self._atc_index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._atc_index_label.setStyleSheet("font-family: monospace; font-size: 20px; color: #a78bfa;")
        step_row2.addWidget(self._atc_index_label, 1)
        next_btn = QPushButton("▶")
        next_btn.clicked.connect(lambda: self._on_atc_step(1))
        step_row2.addWidget(next_btn)
        atc_layout.addLayout(step_row2)
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel(_("LBL_TOOL_COUNT")))
        self._tool_count_spin = QSpinBox()
        self._tool_count_spin.setRange(2, 16)
        self._tool_count_spin.valueChanged.connect(self._on_tool_count_changed)
        count_row.addWidget(self._tool_count_spin)
        atc_layout.addLayout(count_row)
        self._homed_label = QLabel()
        atc_layout.addWidget(self._homed_label)
        row2.addWidget(atc_box)
        layout.addLayout(row2)

        # --- Conveyor -------------------------------------------------
        conveyor_box = QGroupBox(_("LBL_CONVEYOR"))
        conveyor_layout = QHBoxLayout(conveyor_box)
        self._conveyor_not_installed_label = QLabel(_("LBL_CONVEYOR_NOT_INSTALLED"))
        conveyor_layout.addWidget(self._conveyor_not_installed_label)
        self._conveyor_install_btn = QPushButton(_("BTN_MARK_INSTALLED"))
        self._conveyor_install_btn.clicked.connect(self._on_conveyor_install)
        conveyor_layout.addWidget(self._conveyor_install_btn)
        self._conveyor_run_btn = QPushButton()
        self._conveyor_run_btn.clicked.connect(self._on_conveyor_run_toggle)
        conveyor_layout.addWidget(self._conveyor_run_btn)
        self._conveyor_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._conveyor_speed_slider.setRange(0, 100)
        self._conveyor_speed_slider.valueChanged.connect(self._on_conveyor_speed_changed)
        conveyor_layout.addWidget(self._conveyor_speed_slider, 1)
        self._conveyor_speed_label = QLabel("0%")
        conveyor_layout.addWidget(self._conveyor_speed_label)
        layout.addWidget(conveyor_box)

        # --- Endstops -------------------------------------------------
        endstop_box = QGroupBox(_("LBL_ENDSTOPS"))
        endstop_grid = QGridLayout(endstop_box)
        self._endstop_buttons: dict[str, QPushButton] = {}
        for i, (key, label) in enumerate(ENDSTOP_ENTRIES):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _c=False, k=key: self._on_endstop_toggle(k))
            endstop_grid.addWidget(btn, i // 6, i % 6)
            self._endstop_buttons[key] = btn
        layout.addWidget(endstop_box)

        # --- Fans / Pumps / Valves -------------------------------------
        fpv_row = QHBoxLayout()
        self._fan_buttons = self._build_toggle_group(fpv_row, _("LBL_FANS"), 3, self._on_fan_toggle)
        self._pump_buttons = self._build_toggle_group(fpv_row, _("LBL_PUMPS"), 10, self._on_pump_toggle)
        self._valve_buttons = self._build_toggle_group(fpv_row, _("LBL_VALVES"), 10, self._on_valve_toggle)
        layout.addLayout(fpv_row)
        layout.addStretch(1)

        controller.active_state_changed.connect(self._on_state_changed)

    def _build_toggle_group(self, parent_layout: QHBoxLayout, title: str, count: int, on_toggle) -> list[QPushButton]:
        box = QGroupBox(title)
        grid = QGridLayout(box)
        buttons: list[QPushButton] = []
        for i in range(count):
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            btn.clicked.connect(lambda _c=False, idx=i: on_toggle(idx))
            grid.addWidget(btn, i // 5, i % 5)
            buttons.append(btn)
        parent_layout.addWidget(box)
        return buttons

    # --- state sync ----------------------------------------------------

    def _current_controller(self) -> ControllerView | None:
        # Cached from the last real active_state_changed signal, not
        # re-derived from self._controller.active_state - same reasoning
        # as _current_robot on every other panel in this family: this
        # class works purely from the HydraState objects the signal
        # itself carries, so it doesn't depend on a real HydraConnection
        # being registered in self._controller.connections at all (that
        # dict is only populated by real server add_server() calls).
        return self._active_controller

    def _on_state_changed(self, state: HydraState) -> None:
        self._active_controller = state.active_controller
        self._refresh_controls(self._active_controller)

    def _refresh_controls(self, active: ControllerView | None) -> None:
        if active is None:
            return
        stage = active.kinematic_brain_stage

        xy = stage["xyTable"]
        for axis in AXIS_KEYS:
            self._axis_labels[axis].setText(f"{float(xy.get(axis, 0)):.2f}")
        size = xy["tableSize"]
        for spin, field in ((self._width_spin, "width"), (self._length_spin, "length"), (self._height_spin, "height")):
            spin.blockSignals(True)
            spin.setValue(int(size.get(field, 0)))
            spin.blockSignals(False)

        bed = stage["heatedBed"]
        self._therm1_label.setText(f"{float(bed.get('currentTemp1', 0)):.1f}°C")
        self._therm2_label.setText(f"{float(bed.get('currentTemp2', 0)):.1f}°C")
        self._target_temp_spin.blockSignals(True)
        self._target_temp_spin.setValue(int(bed.get("targetTemp", 0)))
        self._target_temp_spin.blockSignals(False)
        ssr_on = bool(bed.get("ssrActive"))
        self._ssr_btn.setText(_("BTN_SSR_ON") if ssr_on else _("BTN_SSR_OFF"))

        atc = stage["atcRevolver"]
        self._atc_index_label.setText(str(int(atc.get("currentIndex", 0)) + 1))
        self._tool_count_spin.blockSignals(True)
        self._tool_count_spin.setValue(int(atc.get("toolCount", 6)))
        self._tool_count_spin.blockSignals(False)
        homed = bool(atc.get("homed"))
        self._homed_label.setText(_("LBL_HOMED") if homed else _("LBL_NOT_HOMED"))

        conveyor = stage["conveyor"]
        installed = bool(conveyor.get("installed"))
        self._conveyor_not_installed_label.setVisible(not installed)
        self._conveyor_install_btn.setVisible(not installed)
        self._conveyor_run_btn.setVisible(installed)
        self._conveyor_speed_slider.setVisible(installed)
        self._conveyor_speed_label.setVisible(installed)
        if installed:
            running = bool(conveyor.get("running"))
            self._conveyor_run_btn.setText(_("LBL_RUNNING") if running else _("LBL_STOPPED"))
            speed = int(conveyor.get("speedPercent", 0))
            self._conveyor_speed_slider.blockSignals(True)
            self._conveyor_speed_slider.setValue(speed)
            self._conveyor_speed_slider.blockSignals(False)
            self._conveyor_speed_label.setText(f"{speed}%")

        endstops = stage["endstops"]
        for key, btn in self._endstop_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(bool(endstops.get(key)))
            btn.blockSignals(False)

        for group, buttons in ((stage["fans"], self._fan_buttons), (stage["pumps"], self._pump_buttons), (stage["valves"], self._valve_buttons)):
            for i, btn in enumerate(buttons):
                if i >= len(group):
                    continue
                btn.blockSignals(True)
                btn.setChecked(bool(group[i]))
                btn.blockSignals(False)

    # --- actions ---------------------------------------------------------

    def _patch(self, updates: dict) -> None:
        active = self._current_controller()
        if active is None:
            return
        stage = active.kinematic_brain_stage
        stage.update(updates)
        active.set_kinematic_brain_stage(stage)
        self._controller.push_active_state()
        self._refresh_controls(active)

    def _on_step_combo_changed(self, index: int) -> None:
        self._jog_step_mm = self._step_combo.itemData(index)

    def _on_jog(self, axis: str, direction: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        stage = active.kinematic_brain_stage
        xy = stage["xyTable"]
        next_value = xy[axis] + direction * self._jog_step_mm
        if axis != "z":
            bound = xy["tableSize"]["width"] if axis == "x" else xy["tableSize"]["length"]
        else:
            bound = xy["tableSize"]["height"]
        next_value = _clamp(next_value, 0, float(bound))
        xy[axis] = next_value
        self._patch({"xyTable": xy})

    def _on_table_size_changed(self, field: str, value: int, lo: int, hi: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        stage = active.kinematic_brain_stage
        stage["xyTable"]["tableSize"][field] = _clamp(value, lo, hi)
        self._patch({"xyTable": stage["xyTable"]})

    def _on_target_temp_changed(self, value: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        bed = active.kinematic_brain_stage["heatedBed"]
        bed["targetTemp"] = _clamp(value, 0, 150)
        self._patch({"heatedBed": bed})

    def _on_ssr_toggle(self) -> None:
        active = self._current_controller()
        if active is None:
            return
        bed = active.kinematic_brain_stage["heatedBed"]
        bed["ssrActive"] = not bed.get("ssrActive")
        self._patch({"heatedBed": bed})

    def _on_atc_step(self, direction: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        atc = active.kinematic_brain_stage["atcRevolver"]
        n = atc["toolCount"]
        next_index = (atc["targetIndex"] + direction) % n
        if next_index < 0:
            next_index += n
        atc["targetIndex"] = next_index
        atc["currentIndex"] = next_index
        atc["homed"] = True
        self._patch({"atcRevolver": atc})

    def _on_tool_count_changed(self, value: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        atc = active.kinematic_brain_stage["atcRevolver"]
        atc["toolCount"] = _clamp(value, 2, 16)
        self._patch({"atcRevolver": atc})

    def _on_conveyor_install(self) -> None:
        active = self._current_controller()
        if active is None:
            return
        conveyor = active.kinematic_brain_stage["conveyor"]
        conveyor["installed"] = True
        self._patch({"conveyor": conveyor})

    def _on_conveyor_run_toggle(self) -> None:
        active = self._current_controller()
        if active is None:
            return
        conveyor = active.kinematic_brain_stage["conveyor"]
        conveyor["running"] = not conveyor.get("running")
        self._patch({"conveyor": conveyor})

    def _on_conveyor_speed_changed(self, value: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        conveyor = active.kinematic_brain_stage["conveyor"]
        conveyor["speedPercent"] = value
        self._patch({"conveyor": conveyor})

    def _on_endstop_toggle(self, key: str) -> None:
        active = self._current_controller()
        if active is None:
            return
        endstops = active.kinematic_brain_stage["endstops"]
        endstops[key] = not endstops.get(key)
        self._patch({"endstops": endstops})

    def _on_fan_toggle(self, index: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        fans = active.kinematic_brain_stage["fans"]
        fans[index] = not fans[index]
        self._patch({"fans": fans})

    def _on_pump_toggle(self, index: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        pumps = active.kinematic_brain_stage["pumps"]
        pumps[index] = not pumps[index]
        self._patch({"pumps": pumps})

    def _on_valve_toggle(self, index: int) -> None:
        active = self._current_controller()
        if active is None:
            return
        valves = active.kinematic_brain_stage["valves"]
        valves[index] = not valves[index]
        self._patch({"valves": valves})
