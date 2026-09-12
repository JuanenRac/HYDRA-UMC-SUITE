# =============================================================================
# HYDRA-UMC-SUITE - Vacuum table model selector and pump/valve controls
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# Real STL geometry with editable footprint; selection preserves other state.
# =============================================================================
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QGroupBox,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.ui.panels.module_config_panel import ModuleConfigPanel

from hydra_suite.vacuum_tables import VACUUM_TABLE_MODELS, vacuum_table_model, select_vacuum_table

class VacuumTablePanel(ModuleConfigPanel):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(controller, "vacuumTable", "HEADING_VACUUM_TABLE", "Vacuum Table", parent)

    def _reset_size_mm(self) -> tuple[int, int]:
        return (160, 120)

    def _display_default_size_mm(self) -> tuple[int, int]:
        return (160, 120)

    def _build_extra_settings(self, settings_layout: QVBoxLayout) -> None:
        self._width_spin.setSingleStep(5)
        self._length_spin.setSingleStep(5)
        settings_layout.addWidget(QLabel(_("LBL_VACUUM_MODEL")))
        self._model_combo = QComboBox()
        for model in VACUUM_TABLE_MODELS:
            self._model_combo.addItem(model["label"], model["id"])
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        settings_layout.addWidget(self._model_combo)
        note = QLabel(_("LBL_VACUUM_MODEL_NOTE"))
        note.setWordWrap(True)
        settings_layout.addWidget(note)
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
        self._model_combo.setCurrentIndex(self._model_combo.findData(vacuum_table_model(module.get("modelId"))["id"]))
        pump_active = bool(module.get("pumpActive", False))
        self._pump_btn.setChecked(pump_active)
        self._pump_btn.setText(_("BTN_PUMP_ON") if pump_active else _("BTN_PUMP_OFF"))
        valve_active = bool(module.get("valveActive", False))
        self._valve_btn.setChecked(valve_active)
        self._valve_btn.setText(_("BTN_VALVE_OPEN") if valve_active else _("BTN_VALVE_CLOSED"))
        self._updating = False

    def _extra_default_fields(self) -> dict[str, Any]:
        return {"pumpActive": False, "valveActive": False, "modelId": VACUUM_TABLE_MODELS[0]["id"]}

    def _on_enable(self) -> None:
        if self._current_robot is not None:
            module = self._current_robot.module(self._module_key)
            if module.get("customSize") is not True:
                module = select_vacuum_table(module, vacuum_table_model(module.get("modelId"))["id"])
            self._current_robot.set_module(self._module_key, module)
        super()._on_enable()

    def _extra_reset_fields(self) -> dict[str, Any]:
        return {"pumpActive": False, "valveActive": False, "modelId": VACUUM_TABLE_MODELS[0]["id"]}

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

    def _on_model_changed(self, index: int) -> None:
        if self._updating or self._current_robot is None:
            return
        module = select_vacuum_table(self._current_robot.module(self._module_key), self._model_combo.itemData(index))
        self._current_robot.set_module(self._module_key, module)
        self._refresh_controls()
        self._push()
