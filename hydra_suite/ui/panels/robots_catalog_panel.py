# =============================================================================
# HYDRA-UMC SUITE - ui/panels/robots_catalog_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Desktop counterpart to HYDRA-UMC-STUDIO's own RobotsCatalogView.tsx -
# every real robot model this ecosystem has kinematics/mesh support for
# (REAL_ROBOT_MODELS, robot_catalog.py - the exact same 24-model set and
# manufacturer labels as STUDIO's own store.tsx ROBOT_MANUFACTURERS, kept
# in sync by hand), filterable by manufacturer/DOF, with a real 3D preview
# of the selected model on the left (a standalone RobotViewport instance,
# the same QOpenGLWidget the main 3D Viewport dock already uses, just
# fed a different model at its own default pose - not a placeholder) and
# a per-model activate/deactivate checkbox writing the same real
# `settings.enabledRobotModels` field STUDIO's own panel writes
# (HydraState.set_robot_model_enabled(), GET/POST /api/settings - the one
# shared settings tree both apps read/write).
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.app import SuiteController
from hydra_suite.i18n import _
from hydra_suite.models import HydraState
from hydra_suite.render.viewport import RobotViewport
from hydra_suite.robot_catalog import REAL_ROBOT_MODELS, ROBOT_MANUFACTURERS, robot_model_dof

_ALL = "__all__"
_MODEL_ROLE = Qt.ItemDataRole.UserRole


class RobotsCatalogPanel(QWidget):
    def __init__(self, controller: SuiteController, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._selected_model = REAL_ROBOT_MODELS[0]
        self._refreshing = False  # guards against _on_item_changed firing while we rebuild the list ourselves

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        self._viewport = RobotViewport()
        outer.addWidget(self._viewport, 1)

        right = QVBoxLayout()
        right.setSpacing(6)

        filters_row = QHBoxLayout()
        self._manufacturer_combo = QComboBox()
        self._manufacturer_combo.addItem(_("OPT_ALL_MANUFACTURERS"), _ALL)
        for manufacturer in sorted(set(ROBOT_MANUFACTURERS.values())):
            self._manufacturer_combo.addItem(manufacturer, manufacturer)
        self._manufacturer_combo.currentIndexChanged.connect(self._rebuild_list)
        filters_row.addWidget(self._manufacturer_combo)

        self._dof_combo = QComboBox()
        self._dof_combo.addItem(_("OPT_ALL_DOF"), _ALL)
        self._dof_combo.addItem("5-DOF", 5)
        self._dof_combo.addItem("6-DOF", 6)
        self._dof_combo.currentIndexChanged.connect(self._rebuild_list)
        filters_row.addWidget(self._dof_combo)
        right.addLayout(filters_row)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemChanged.connect(self._on_item_changed)
        right.addWidget(self._list, 1)

        outer.addLayout(right, 1)

        self._rebuild_list()
        controller.active_state_changed.connect(self._on_state_changed)

    # --- filtering/list -----------------------------------------------------

    def _filtered_models(self) -> list[str]:
        manufacturer = self._manufacturer_combo.currentData()
        dof = self._dof_combo.currentData()
        models = REAL_ROBOT_MODELS
        if manufacturer != _ALL:
            models = [m for m in models if ROBOT_MANUFACTURERS[m] == manufacturer]
        if dof != _ALL:
            models = [m for m in models if robot_model_dof(m) == dof]
        return models

    def _rebuild_list(self) -> None:
        self._refreshing = True
        try:
            self._list.clear()
            state = self._controller.active_state
            for model in self._filtered_models():
                enabled = state.is_robot_model_enabled(model) if state is not None else True
                item = QListWidgetItem(f"{model} · {ROBOT_MANUFACTURERS[model]}")
                item.setData(_MODEL_ROLE, model)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
                self._list.addItem(item)
        finally:
            self._refreshing = False

    def _on_state_changed(self, state: HydraState) -> None:
        self._rebuild_list()

    # --- selection/preview ---------------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        model = item.data(_MODEL_ROLE)
        if model is None:
            return
        self._selected_model = model
        self._viewport.set_robot_model(model)

    # --- activate/deactivate --------------------------------------------------

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._refreshing:
            return
        model = item.data(_MODEL_ROLE)
        if model is None:
            return
        state = self._controller.active_state
        if state is None:
            return
        state.set_robot_model_enabled(model, item.checkState() == Qt.CheckState.Checked)
        self._controller.push_active_state()
