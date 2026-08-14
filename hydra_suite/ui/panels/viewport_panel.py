# =============================================================================
# HYDRA-UMC SUITE - ui/panels/viewport_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Wraps render/viewport.py's RobotViewport, keeping it posed from whichever
# robot ui/panels/robot_control.py currently has selected. Only UR3e/5e/
# 10e/16e/20's shared geometry family has real STL+kinematics data ported
# into this Python app so far (see kinematics.py's own header) - honestly
# says so instead of silently rendering the wrong robot when a Parol6/
# Faze4/AR3/AR4 is selected, matching this ecosystem's own established
# "don't overstate what's real" documentation convention.
# =============================================================================
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, RobotView
from hydra_suite.render.viewport import RobotViewport

SUPPORTED_MODELS = {"UR5e (6-DOF)"}  # see docs/ROADMAP.md for extending to the sibling UR models


class ViewportPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._current_robot_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        heading = QLabel("3D VIEWPORT")
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)

        self._stack = QStackedWidget()
        self._viewport = RobotViewport()
        self._stack.addWidget(self._viewport)

        self._unsupported_label = QLabel()
        self._unsupported_label.setWordWrap(True)
        self._unsupported_label.setStyleSheet("color: #7f8ea1; padding: 24px;")
        self._unsupported_label.setAlignment(self._unsupported_label.alignment())
        self._stack.addWidget(self._unsupported_label)

        layout.addWidget(self._stack, 1)

        hint = QLabel("Left-drag: orbit   •   Right/middle-drag: pan   •   Wheel: zoom")
        hint.setStyleSheet("color: #4a5563; font-size: 11px;")
        layout.addWidget(hint)

        controller.active_state_changed.connect(self._on_state_changed)

    def set_selected_robot(self, robot: RobotView | None) -> None:
        self._current_robot_id = robot.id if robot else None
        self._apply(robot)

    def _on_state_changed(self, state: HydraState) -> None:
        if self._current_robot_id is None:
            return
        active = state.active_controller
        robot = active.robot_by_id(self._current_robot_id) if active is not None else None
        self._apply(robot)

    def _apply(self, robot: RobotView | None) -> None:
        if robot is None:
            self._unsupported_label.setText("No robot selected.")
            self._stack.setCurrentWidget(self._unsupported_label)
            return
        if robot.model not in SUPPORTED_MODELS:
            self._unsupported_label.setText(
                f"'{robot.model}' has no real 3D mesh/kinematics in HYDRA-UMC SUITE yet.\n\n"
                f"Only {', '.join(sorted(SUPPORTED_MODELS))} is wired up in this version "
                "(same real STL + forward-kinematics data HYDRA-UMC-STUDIO's own web UI "
                "uses for it) - see docs/ROADMAP.md for extending this to the other models."
            )
            self._stack.setCurrentWidget(self._unsupported_label)
            return
        self._stack.setCurrentWidget(self._viewport)
        self._viewport.set_joints_deg(robot.joints)
