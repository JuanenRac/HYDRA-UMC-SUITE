# =============================================================================
# HYDRA-UMC SUITE - ui/panels/heated_bed_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The Heated Bed module config panel - ports HYDRA-UMC-STUDIO's own
# HeatedBedConfig.tsx via module_config_panel.py's shared ModuleConfigPanel
# (robot selector, enable/disable, width/length, reset) plus this module's
# own extra shape: an SSR (solid-state relay) on/off toggle, a real
# user-set target temperature, and two read-only thermistor readouts.
# The thermistor values are real telemetry fields on the module dict
# (currentTemp1/currentTemp2) - this panel only DISPLAYS them, the same
# way STUDIO's own component does; nothing here simulates or invents a
# temperature curve.
#
# Deliberately does NOT port HeatedBedConfig.tsx's own right-hand "3D
# Live View" - see module_config_panel.py's own header for why (no
# render/viewport.py support yet for an attached tool module's own
# geometry). See this repo's own [[project_suite_studio_parity_gap]] for
# the full list of still-pending panels this reasoning also applies to.
# =============================================================================
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.ui.panels.module_config_panel import ModuleConfigPanel

DEFAULT_TARGET_TEMP_C = 60
DEFAULT_AMBIENT_TEMP_C = 25.0


class HeatedBedPanel(ModuleConfigPanel):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(controller, "heatedBed", "HEADING_HEATED_BED", "Heated Bed", parent)

    def _build_extra_settings(self, settings_layout: QVBoxLayout) -> None:
        heating_box = QGroupBox(_("GROUP_HEATING_CONTROLS"))
        heating_layout = QVBoxLayout(heating_box)

        ssr_row = QHBoxLayout()
        ssr_row.addStretch(1)
        self._ssr_btn = QPushButton(_("BTN_SSR_OFF"))
        self._ssr_btn.setCheckable(True)
        self._ssr_btn.setStyleSheet(
            "QPushButton:checked { background-color: #f43f5e; color: white; font-weight: 600; }"
        )
        self._ssr_btn.toggled.connect(self._on_ssr_toggled)
        ssr_row.addWidget(self._ssr_btn)
        heating_layout.addLayout(ssr_row)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel(_("LBL_TARGET_TEMP")))
        self._target_spin = QSpinBox()
        self._target_spin.setRange(0, 300)
        self._target_spin.setSuffix(" °C")
        self._target_spin.valueChanged.connect(self._on_target_temp_changed)
        target_row.addWidget(self._target_spin)
        target_row.addStretch(1)
        heating_layout.addLayout(target_row)

        temps_row = QHBoxLayout()
        self._temp1_label = QLabel()
        self._temp2_label = QLabel()
        for name_text, value_label in (
            (_("LBL_THERMISTOR_1"), self._temp1_label),
            (_("LBL_THERMISTOR_2"), self._temp2_label),
        ):
            col = QVBoxLayout()
            name = QLabel(name_text)
            name.setStyleSheet("color: #7f8ea1; font-size: 10px; font-weight: 700;")
            value_label.setStyleSheet("color: #fb923c; font-family: monospace; font-size: 16px;")
            col.addWidget(name)
            col.addWidget(value_label)
            temps_row.addLayout(col)
        temps_row.addStretch(1)
        heating_layout.addLayout(temps_row)

        settings_layout.addWidget(heating_box)

    def _refresh_extra_controls(self, module: dict[str, Any]) -> None:
        self._updating = True
        self._target_spin.setValue(int(module.get("targetTemp", DEFAULT_TARGET_TEMP_C)))
        ssr_active = bool(module.get("ssrActive", False))
        self._ssr_btn.setChecked(ssr_active)
        self._ssr_btn.setText(_("BTN_SSR_ON") if ssr_active else _("BTN_SSR_OFF"))
        self._temp1_label.setText(f"{float(module.get('currentTemp1', DEFAULT_AMBIENT_TEMP_C)):.1f} °C")
        self._temp2_label.setText(f"{float(module.get('currentTemp2', DEFAULT_AMBIENT_TEMP_C)):.1f} °C")
        self._updating = False

    def _extra_default_fields(self) -> dict[str, Any]:
        return {
            "targetTemp": DEFAULT_TARGET_TEMP_C,
            "currentTemp1": DEFAULT_AMBIENT_TEMP_C,
            "currentTemp2": DEFAULT_AMBIENT_TEMP_C,
            "ssrActive": False,
        }

    def _extra_reset_fields(self) -> dict[str, Any]:
        return {
            "targetTemp": DEFAULT_TARGET_TEMP_C,
            "currentTemp1": DEFAULT_AMBIENT_TEMP_C,
            "currentTemp2": DEFAULT_AMBIENT_TEMP_C,
            "ssrActive": False,
        }

    def _on_ssr_toggled(self, checked: bool) -> None:
        if self._updating or self._current_robot is None:
            return
        self._ssr_btn.setText(_("BTN_SSR_ON") if checked else _("BTN_SSR_OFF"))
        module = dict(self._current_robot.module(self._module_key))
        module["ssrActive"] = checked
        self._current_robot.set_module(self._module_key, module)
        self._push()

    def _on_target_temp_changed(self, value: int) -> None:
        if self._updating or self._current_robot is None:
            return
        module = dict(self._current_robot.module(self._module_key))
        module["targetTemp"] = value
        self._current_robot.set_module(self._module_key, module)
        self._push()
