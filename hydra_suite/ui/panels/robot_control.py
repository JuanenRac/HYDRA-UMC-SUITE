# =============================================================================
# HYDRA-UMC SUITE - ui/panels/robot_control.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Robot selection + jog control - the desktop counterpart to
# HYDRA-UMC-STUDIO's own RobotDetail.tsx jog panel: a rotary knob + slider
# per joint (matching that component's own RotaryKnob+FuturisticSlider
# pairing), speed/acceleration controls, live-pushes every change back to
# the server the same way HYDRA-UMC-STUDIO's own debounced save-effect
# does (see net/client.py's own push_state()).
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState, JOINT_NAMES, RobotView
from hydra_suite.ui.widgets.rotary_knob import RotaryKnob

JOINT_RANGE_DEG = (-180.0, 180.0)
SLIDER_SCALE = 10  # QSlider only does integers - 0.1deg resolution


class JointRow(QWidget):
    changed = Signal(str, float)  # joint name, new value

    def __init__(self, joint_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.joint_name = joint_name
        self._updating = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(joint_name.upper())
        label.setFixedWidth(28)
        label.setStyleSheet("color: #7f8ea1; font-weight: 600;")
        layout.addWidget(label)

        self.knob = RotaryKnob(*JOINT_RANGE_DEG)
        self.knob.setFixedSize(48, 48)
        layout.addWidget(self.knob)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(JOINT_RANGE_DEG[0] * SLIDER_SCALE), int(JOINT_RANGE_DEG[1] * SLIDER_SCALE))
        layout.addWidget(self.slider, 1)

        self.value_label = QLabel("0.0°")
        self.value_label.setFixedWidth(50)
        layout.addWidget(self.value_label)

        self.knob.valueChanged.connect(self._on_knob_changed)
        self.slider.valueChanged.connect(self._on_slider_changed)

    def set_value(self, value: float) -> None:
        self._updating = True
        self.knob.setValue(value)
        self.slider.setValue(int(value * SLIDER_SCALE))
        self.value_label.setText(f"{value:.1f}°")
        self._updating = False

    def _on_knob_changed(self, value: float) -> None:
        if self._updating:
            return
        self.set_value(value)
        self.changed.emit(self.joint_name, value)

    def _on_slider_changed(self, raw: int) -> None:
        if self._updating:
            return
        value = raw / SLIDER_SCALE
        self.set_value(value)
        self.changed.emit(self.joint_name, value)


class RobotControlPanel(QWidget):
    robot_selected = Signal(object)  # RobotView | None - other panels (viewport) listen to this

    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_robot: RobotView | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel(_("HEADING_ROBOT_CONTROL"))
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        self._robot_combo = QComboBox()
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        layout.addWidget(self._robot_combo)

        joints_box = QGroupBox(_("GROUP_JOINTS"))
        joints_layout = QVBoxLayout(joints_box)
        self._joint_rows: dict[str, JointRow] = {}
        for name in JOINT_NAMES:
            row = JointRow(name)
            row.changed.connect(self._on_joint_changed)
            joints_layout.addWidget(row)
            self._joint_rows[name] = row
        layout.addWidget(joints_box)

        speed_box = QGroupBox(_("GROUP_PLAYBACK"))
        speed_layout = QGridLayout(speed_box)
        speed_layout.addWidget(QLabel(_("LBL_SPEED")), 0, 0)
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(1, 200)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self._speed_slider, 0, 1)
        self._speed_label = QLabel("100%")
        speed_layout.addWidget(self._speed_label, 0, 2)

        speed_layout.addWidget(QLabel(_("LBL_ACCELERATION")), 1, 0)
        self._accel_slider = QSlider(Qt.Orientation.Horizontal)
        self._accel_slider.setRange(1, 200)
        self._accel_slider.valueChanged.connect(self._on_accel_changed)
        speed_layout.addWidget(self._accel_slider, 1, 1)
        self._accel_label = QLabel("100%")
        speed_layout.addWidget(self._accel_label, 1, 2)
        layout.addWidget(speed_box)

        layout.addStretch(1)

        controller.active_state_changed.connect(self._on_state_changed)

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
        self.robot_selected.emit(self._current_robot)

    def _on_robot_combo_changed(self, index: int) -> None:
        active = self._controller.active_state.active_controller if self._controller.active_state else None
        robots = active.robots if active is not None else []
        self._current_robot = robots[index] if 0 <= index < len(robots) else None
        self._refresh_controls()
        self.robot_selected.emit(self._current_robot)

    def _refresh_controls(self) -> None:
        robot = self._current_robot
        for name, row in self._joint_rows.items():
            row.blockSignals(True)
            row.set_value(robot.joints[name] if robot else 0.0)
            row.blockSignals(False)
        self._speed_slider.blockSignals(True)
        self._accel_slider.blockSignals(True)
        self._speed_slider.setValue(int(robot.speed) if robot else 100)
        self._accel_slider.setValue(int(robot.acceleration) if robot else 100)
        self._speed_label.setText(f"{self._speed_slider.value()}%")
        self._accel_label.setText(f"{self._accel_slider.value()}%")
        self._speed_slider.blockSignals(False)
        self._accel_slider.blockSignals(False)
        enabled = robot is not None
        for row in self._joint_rows.values():
            row.setEnabled(enabled)
        self._speed_slider.setEnabled(enabled)
        self._accel_slider.setEnabled(enabled)

    def _on_joint_changed(self, joint_name: str, value: float) -> None:
        if self._current_robot is None:
            return
        self._current_robot.set_joint(joint_name, value)
        self._controller.push_active_state()

    def _on_speed_changed(self, value: int) -> None:
        self._speed_label.setText(f"{value}%")
        if self._current_robot is None:
            return
        # Atomic 'speed' command instead of mutating state + a full-tree
        # push_active_state() - see net/client.py's own send_command()
        # comment / DISEÑO_SYNC_DELTAS.txt CAUSA A. local_mutate gives
        # instant optimistic feedback (rolled back if the request fails);
        # every other client's state updates via the WS delta round-trip,
        # same as before.
        self._controller.send_robot_command(self._current_robot.id, "speed", {"speed": value}, lambda r: r.set_speed(value))

    def _on_accel_changed(self, value: int) -> None:
        self._accel_label.setText(f"{value}%")
        if self._current_robot is None:
            return
        self._controller.send_robot_command(self._current_robot.id, "speed", {"acceleration": value}, lambda r: r.set_acceleration(value))
