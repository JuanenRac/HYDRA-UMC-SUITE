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
# Four detailed 5 mm STL presets share the live module renderer with STUDIO.
# Size edits are visual configuration only; they never enable the heater.
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
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.ui.panels.module_config_panel import ModuleConfigPanel
from hydra_suite.heated_beds import HEATED_BED_MODELS, heated_bed_model, select_heated_bed

DEFAULT_TARGET_TEMP_C = 60
DEFAULT_AMBIENT_TEMP_C = 25.0


class HeatedBedPanel(ModuleConfigPanel):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(controller, "heatedBed", "HEADING_HEATED_BED", "Heated Bed", parent)

    def _build_extra_settings(self, settings_layout: QVBoxLayout) -> None:
        for spin in (self._width_spin, self._length_spin):
            spin.setRange(25, 5000)
            spin.setSingleStep(5)
        settings_layout.addWidget(QLabel(_("LBL_HEATED_MODEL")))
        self._model_combo = QComboBox()
        for model in HEATED_BED_MODELS:
            self._model_combo.addItem(model["label"], model["id"])
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        settings_layout.addWidget(self._model_combo)
        note = QLabel(_("LBL_HEATED_MODEL_NOTE"))
        note.setWordWrap(True)
        settings_layout.addWidget(note)
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
        self._model_combo.setCurrentIndex(self._model_combo.findData(heated_bed_model(module.get("modelId"))["id"]))
        self._target_spin.setValue(int(module.get("targetTemp", DEFAULT_TARGET_TEMP_C)))
        ssr_active = bool(module.get("ssrActive", False))
        self._ssr_btn.setChecked(ssr_active)
        self._ssr_btn.setText(_("BTN_SSR_ON") if ssr_active else _("BTN_SSR_OFF"))
        self._temp1_label.setText(f"{float(module.get('currentTemp1', DEFAULT_AMBIENT_TEMP_C)):.1f} °C")
        self._temp2_label.setText(f"{float(module.get('currentTemp2', DEFAULT_AMBIENT_TEMP_C)):.1f} °C")
        self._updating = False

    def _extra_default_fields(self) -> dict[str, Any]:
        return {
            "modelId": "200x200x5",
            "targetTemp": DEFAULT_TARGET_TEMP_C,
            "currentTemp1": DEFAULT_AMBIENT_TEMP_C,
            "currentTemp2": DEFAULT_AMBIENT_TEMP_C,
            "ssrActive": False,
        }

    def _extra_reset_fields(self) -> dict[str, Any]:
        return {
            "modelId": "200x200x5",
            "targetTemp": DEFAULT_TARGET_TEMP_C,
            "currentTemp1": DEFAULT_AMBIENT_TEMP_C,
            "currentTemp2": DEFAULT_AMBIENT_TEMP_C,
            "ssrActive": False,
        }

    def _display_default_size_mm(self) -> tuple[int, int]:
        return (200, 200)

    def _on_model_changed(self, index: int) -> None:
        if self._updating or self._current_robot is None:
            return
        module = select_heated_bed(self._current_robot.module(self._module_key), self._model_combo.itemData(index))
        self._current_robot.set_module(self._module_key, module)
        self._refresh_controls()
        self._push()

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
