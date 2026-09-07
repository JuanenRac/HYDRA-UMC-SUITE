# =============================================================================
# HYDRA-UMC SUITE - ui/panels/vacuum_table_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The Vacuum Table module config panel - ports HYDRA-UMC-STUDIO's own
# VacuumTableConfig.tsx via module_config_panel.py's shared
# ModuleConfigPanel (robot selector, enable/disable, width/length, reset)
# plus this module's own extra shape: a real Pump on/off toggle and a
# real Valve open/closed toggle. Real, if minor, quirk carried over
# faithfully from the source component: VacuumTableConfig.tsx's own
# width/length display FALLS BACK to 500mm (same as CNC/Laser/HeatedBed)
# but its own handleReset() writes 100mm - a genuine mismatch in
# STUDIO itself between the enable-time display default and the
# reset-time write default, reproduced here via
# ModuleConfigPanel._default_size_mm() rather than silently picking one
# of the two numbers.
#
# Deliberately does NOT port VacuumTableConfig.tsx's own right-hand "3D
# Live View" - see module_config_panel.py's own header for why. See this
# repo's own [[project_suite_studio_parity_gap]] for the full list of
# still-pending panels this reasoning also applies to.
#
# Note: only _reset_size_mm() is overridden here, not
# _display_default_size_mm() - the enable-time display fallback really is
# 500 in STUDIO's own source (`moduleData?.size?.width || 500`, same as
# CNC/Laser/HeatedBed), it's specifically handleReset() that disagrees
# with it and writes 100. See module_config_panel.py's own header for
# the full reasoning.
# =============================================================================
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.ui.panels.module_config_panel import ModuleConfigPanel

DEFAULT_RESET_SIZE_MM = 100


class VacuumTablePanel(ModuleConfigPanel):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(controller, "vacuumTable", "HEADING_VACUUM_TABLE", "Vacuum Table", parent)

    def _reset_size_mm(self) -> tuple[int, int]:
        return (DEFAULT_RESET_SIZE_MM, DEFAULT_RESET_SIZE_MM)

    def _build_extra_settings(self, settings_layout: QVBoxLayout) -> None:
        controls_box = QGroupBox(_("GROUP_VACUUM_CONTROLS"))
        controls_row = QHBoxLayout(controls_box)

        self._pump_btn = QPushButton(_("BTN_PUMP_OFF"))
        self._pump_btn.setCheckable(True)
        self._pump_btn.setStyleSheet(
            "QPushButton:checked { background-color: #0ea5e9; color: white; font-weight: 600; }"
        )
        self._pump_btn.toggled.connect(self._on_pump_toggled)
        controls_row.addWidget(self._pump_btn)

        self._valve_btn = QPushButton(_("BTN_VALVE_CLOSED"))
        self._valve_btn.setCheckable(True)
        self._valve_btn.setStyleSheet(
            "QPushButton:checked { background-color: #0ea5e9; color: white; font-weight: 600; }"
        )
        self._valve_btn.toggled.connect(self._on_valve_toggled)
        controls_row.addWidget(self._valve_btn)

        settings_layout.addWidget(controls_box)

    def _refresh_extra_controls(self, module: dict[str, Any]) -> None:
        self._updating = True
        pump_active = bool(module.get("pumpActive", False))
        self._pump_btn.setChecked(pump_active)
        self._pump_btn.setText(_("BTN_PUMP_ON") if pump_active else _("BTN_PUMP_OFF"))
        valve_active = bool(module.get("valveActive", False))
        self._valve_btn.setChecked(valve_active)
        self._valve_btn.setText(_("BTN_VALVE_OPEN") if valve_active else _("BTN_VALVE_CLOSED"))
        self._updating = False

    def _extra_default_fields(self) -> dict[str, Any]:
        return {"pumpActive": False, "valveActive": False}

    def _extra_reset_fields(self) -> dict[str, Any]:
        return {"pumpActive": False, "valveActive": False}

    def _on_pump_toggled(self, checked: bool) -> None:
        if self._updating or self._current_robot is None:
            return
        self._pump_btn.setText(_("BTN_PUMP_ON") if checked else _("BTN_PUMP_OFF"))
        module = dict(self._current_robot.module(self._module_key))
        module["pumpActive"] = checked
        self._current_robot.set_module(self._module_key, module)
        self._push()

    def _on_valve_toggled(self, checked: bool) -> None:
        if self._updating or self._current_robot is None:
            return
        self._valve_btn.setText(_("BTN_VALVE_OPEN") if checked else _("BTN_VALVE_CLOSED"))
        module = dict(self._current_robot.module(self._module_key))
        module["valveActive"] = checked
        self._current_robot.set_module(self._module_key, module)
        self._push()
