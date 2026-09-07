# =============================================================================
# HYDRA-UMC SUITE - ui/panels/module_config_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Generic tool-attachment config panel - ports the shared shape behind
# HYDRA-UMC-STUDIO's own CNC.tsx/Laser.tsx (the two are otherwise
# byte-for-byte identical React components, differing only in the module
# key, heading and icon): a robot selector, an enable/disable toggle with
# a real empty state, width/length (mm) size fields, and a reset action.
# One class parameterized by module_key/title covers both real panels
# (see cnc_panel.py/laser_panel.py) instead of duplicating this shape
# twice, matching [[feedback_no_reference_reuse_dont_invent]] - a
# spec-less variant reuses the existing baseline instead of a fresh
# design, and STUDIO's own two source files already ARE that baseline
# duplicated once; this does not need to happen again on the Qt side.
#
# A module with MORE than size (e.g. heated_bed_panel.py's own heating
# controls) subclasses this and overrides the 4 extension points below
# (_build_extra_settings/_refresh_extra_controls/_extra_default_fields/
# _extra_reset_fields) rather than re-implementing the shared robot
# selector/enable-disable/size/reset shape a second time.
#
# Also ports CNC.tsx/Laser.tsx's own right-hand "3D Live View" for real
# (a react-three-fiber <Canvas> rendering Shared3DEnvironment +
# SharedModule3DView) - a dedicated RobotViewport instance
# (render/viewport.py) switched into module-only mode
# (set_attached_module(), render/module_rig.py) rather than the shared
# robot viewport, matching STUDIO's own per-panel <Canvas> (each of
# these screens owns its own 3D view there too, not a shared one). Not
# every module_key has real preview geometry ported yet -
# module_rig.py's own module_segments() returns an empty list (a blank
# but real, not stubbed-with-a-placeholder, viewport) for anything
# outside CNC/Laser/HeatedBed/VacuumTable - see that file's own header.
#
# Writes via push_active_state() (a full-tree settings mutation), matching
# STUDIO's own updateRobot() - not the atomic send_robot_command() path,
# since there is no server-side atomic case for "reconfigure a tool
# module" the way there is for "jog"/"play"/"pause"/"stop".
# =============================================================================
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
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
from hydra_suite.render.viewport import RobotViewport

DEFAULT_SIZE_MM = 500


class ModuleConfigPanel(QWidget):
    def __init__(
        self,
        controller: SuiteController,
        module_key: str,
        heading_key: str,
        machine_name: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._controller = controller
        self._module_key = module_key
        self._machine_name = machine_name
        self._current_robot: RobotView | None = None
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        heading = QLabel(_(heading_key))
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

        # Page 0: no module configured yet.
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        empty_title = QLabel(_("LBL_NO_MODULE_ASSIGNED", machine=machine_name))
        empty_title.setStyleSheet("font-weight: 600; color: #cfd8e3;")
        empty_layout.addWidget(empty_title)
        empty_desc = QLabel(_("LBL_NO_MODULE_DESC"))
        empty_desc.setWordWrap(True)
        empty_desc.setStyleSheet("color: #7f8ea1;")
        empty_layout.addWidget(empty_desc)
        self._enable_btn = QPushButton(_("BTN_ENABLE_MODULE", machine=machine_name))
        self._enable_btn.clicked.connect(self._on_enable)
        empty_layout.addWidget(self._enable_btn)
        empty_layout.addStretch(2)
        self._stack.addWidget(empty_page)

        # Page 1: module settings + live 3D preview, side by side - matches
        # STUDIO's own CNC.tsx/Laser.tsx two-column layout (settings form
        # on the left, its own <Canvas> on the right) rather than stacking
        # them, since both fit comfortably at this panel's own real width.
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

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel(_("LBL_WIDTH_X")))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(10, 5000)
        self._width_spin.setSingleStep(10)
        self._width_spin.setSuffix(" mm")
        self._width_spin.valueChanged.connect(self._on_width_changed)
        size_row.addWidget(self._width_spin)
        size_row.addWidget(QLabel(_("LBL_LENGTH_Y")))
        self._length_spin = QSpinBox()
        self._length_spin.setRange(10, 5000)
        self._length_spin.setSingleStep(10)
        self._length_spin.setSuffix(" mm")
        self._length_spin.valueChanged.connect(self._on_length_changed)
        size_row.addWidget(self._length_spin)
        settings_box_layout.addLayout(size_row)

        settings_layout.addWidget(settings_box)
        self._build_extra_settings(settings_layout)
        settings_layout.addStretch(1)
        settings_page_layout.addWidget(settings_column, 1)

        self._module_viewport = RobotViewport()
        self._module_viewport.setMinimumWidth(220)
        settings_page_layout.addWidget(self._module_viewport, 1)

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
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        robot = self._current_robot
        has_robot = robot is not None
        enabled = has_robot and robot.module_enabled(self._module_key)

        self._reset_btn.setVisible(enabled)
        self._robot_combo.setEnabled(has_robot)
        self._stack.setCurrentIndex(1 if enabled else 0)
        self._enable_btn.setEnabled(has_robot)

        if not enabled:
            self._module_viewport.set_attached_module(None)
            return

        module = robot.module(self._module_key)
        size = module.get("size") or {}
        default_width, default_length = self._display_default_size_mm()
        width_mm = size.get("width", default_width)
        length_mm = size.get("length", default_length)
        self._updating = True
        self._width_spin.setValue(int(width_mm))
        self._length_spin.setValue(int(length_mm))
        self._updating = False
        self._refresh_extra_controls(module)
        self._module_viewport.set_attached_module(self._module_key, float(width_mm), float(length_mm))

    # --- extension points for a module with more than size (e.g.
    # heated_bed_panel.py's own heating controls) - no-op by default so
    # CNC/Laser, which have nothing extra, are unaffected. ------------

    def _build_extra_settings(self, settings_layout: QVBoxLayout) -> None:
        """Add module-specific widgets below the shared size group box."""
        return

    def _refresh_extra_controls(self, module: dict[str, Any]) -> None:
        """Sync any extra widgets added by _build_extra_settings()."""
        return

    def _display_default_size_mm(self) -> tuple[int, int]:
        """(width, length) mm shown when no "size" has been written yet -
        mirrors STUDIO's own `moduleData?.size?.width || 500` UI-only
        fallback, which is 500 for every module including VacuumTable
        (see _reset_size_mm() for why that one still needs its own
        override elsewhere)."""
        return (DEFAULT_SIZE_MM, DEFAULT_SIZE_MM)

    def _reset_size_mm(self) -> tuple[int, int]:
        """(width, length) mm actually WRITTEN by Reset. STUDIO's own
        per-module handleReset()s don't all agree with their own
        enable-time display fallback above: CNC/Laser/HeatedBed reset to
        500 (same as the display fallback), VacuumTable resets to 100
        (while still DISPLAYING 500 before that first reset) - a real,
        if minor, inconsistency in STUDIO itself, reproduced faithfully
        here via two separate hooks rather than collapsing them into one
        number."""
        return self._display_default_size_mm()

    def _extra_default_fields(self) -> dict[str, Any]:
        """Extra fields (beyond size) set via setdefault on first enable."""
        return {}

    def _extra_reset_fields(self) -> dict[str, Any]:
        """Extra fields (beyond size/worldPos/worldRot/renderScale) included
        in the reset payload."""
        return {}

    # --- writes ----------------------------------------------------------

    def _push(self) -> None:
        self._controller.push_active_state()

    def _on_enable(self) -> None:
        if self._current_robot is None:
            return
        module = dict(self._current_robot.module(self._module_key))
        module["enabled"] = True
        # No "size" setdefault here, matching STUDIO's own handleToggle()
        # exactly: enabling writes only `enabled`, and the width/length
        # spinboxes fall back to _display_default_size_mm() purely for
        # DISPLAY (see _refresh_controls()) until something actually
        # writes a size - a real size change, or Reset (_reset_size_mm()).
        # This split matters because STUDIO's own per-module
        # handleReset()s don't all agree with their own enable-time
        # display fallback (VacuumTable shows 500 on enable but resets to
        # 100) - persisting a default here would silently pick one of
        # those two numbers for every module.
        for key, default in self._extra_default_fields().items():
            module.setdefault(key, default)
        self._current_robot.set_module(self._module_key, module)
        self._refresh_controls()
        self._push()

    def _on_disable(self) -> None:
        if self._current_robot is None:
            return
        module = dict(self._current_robot.module(self._module_key))
        module["enabled"] = False
        self._current_robot.set_module(self._module_key, module)
        self._refresh_controls()
        self._push()

    def _on_reset(self) -> None:
        if self._current_robot is None:
            return
        reset_width, reset_length = self._reset_size_mm()
        payload: dict[str, Any] = {
            "enabled": True,
            "size": {"width": reset_width, "length": reset_length},
            "worldPos": {"x": 0, "y": 0},
            "worldRot": 0,
            "renderScale": 1,
        }
        payload.update(self._extra_reset_fields())
        self._current_robot.set_module(self._module_key, payload)
        self._refresh_controls()
        self._push()

    def _on_width_changed(self, value: int) -> None:
        self._on_size_changed("width", value)

    def _on_length_changed(self, value: int) -> None:
        self._on_size_changed("length", value)

    def _on_size_changed(self, axis: str, value: int) -> None:
        if self._updating or self._current_robot is None:
            return
        module = dict(self._current_robot.module(self._module_key))
        size = dict(module.get("size") or {})
        size[axis] = value
        module["size"] = size
        self._current_robot.set_module(self._module_key, module)
        # Updates the live 3D preview immediately, matching STUDIO's own
        # reactive <Canvas> (it re-renders on every keystroke, not only
        # once the server echoes the write back) - without this, dragging
        # the width/length spinbox would leave the preview showing the
        # OLD size until the next state broadcast round-trips, which on a
        # slow/disconnected link could be seconds or never.
        self._refresh_controls()
        self._push()
