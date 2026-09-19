"""Real assertion-based coverage for RobotsCatalogPanel (ui/panels/
robots_catalog_panel.py) and HydraState.is_robot_model_enabled/
set_robot_model_enabled (models.py) - the SUITE-side port of
HYDRA-UMC-STUDIO's own RobotsCatalogView.tsx. Headless: a real
QApplication, a fake HydraConnection (types.SimpleNamespace, matching
tests/verify_cameras_panel.py's own pattern), no real network."""
import asyncio
import sys
import types

import qasync
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState
from hydra_suite.render.kinematics import ROBOT_REGISTRY
from hydra_suite.robot_catalog import REAL_ROBOT_MODELS, ROBOT_MANUFACTURERS, robot_model_dof
from hydra_suite.ui.panels.robots_catalog_panel import RobotsCatalogPanel


def _run() -> None:
    # --- catalog data stays in sync with the real kinematics registry ------
    registry_models = set(ROBOT_REGISTRY.keys()) - {"Generic (6-DOF)"}
    assert set(REAL_ROBOT_MODELS) == registry_models, (
        "robot_catalog.py's own model list has drifted from render/kinematics.py's real ROBOT_REGISTRY"
    )
    assert robot_model_dof("SO-ARM100 (5-DOF)") == 5
    assert robot_model_dof("UR5e (6-DOF)") == 6
    print("robot_catalog.REAL_ROBOT_MODELS/robot_model_dof: PASS")

    # --- HydraState.is_robot_model_enabled/set_robot_model_enabled ---------
    state = HydraState({"settings": {}, "controllers": [], "activeControllerId": ""})
    assert state.is_robot_model_enabled("UR5e (6-DOF)") is True, "an unset model must read as enabled"
    state.set_robot_model_enabled("UR5e (6-DOF)", False)
    assert state.is_robot_model_enabled("UR5e (6-DOF)") is False
    assert state.is_robot_model_enabled("AR3 (6-DOF)") is True, "toggling one model must not affect another"
    state.set_robot_model_enabled("UR5e (6-DOF)", True)
    assert state.is_robot_model_enabled("UR5e (6-DOF)") is True
    print("HydraState.is_robot_model_enabled/set_robot_model_enabled: PASS")

    # --- RobotsCatalogPanel, headless, real Qt widgets ---------------------
    app = QApplication.instance() or QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    controller = SuiteController()

    push_calls: list[bool] = []

    async def _noop_push_state() -> None:
        push_calls.append(True)

    live_state = HydraState({"settings": {}, "controllers": [], "activeControllerId": ""})
    controller.connections["c1"] = types.SimpleNamespace(state=live_state, push_state=_noop_push_state)
    controller._active_id = "c1"

    panel = RobotsCatalogPanel(controller)
    assert panel._list.count() == len(REAL_ROBOT_MODELS), "no filter applied yet - every real model must be listed"
    first_item = panel._list.item(0)
    assert first_item.checkState() == Qt.CheckState.Checked, "an unset model must start checked (enabled)"
    print("RobotsCatalogPanel initial list, all models enabled by default: PASS")

    # Selecting a row updates the 3D preview's own current model.
    ar3_row = next(i for i in range(panel._list.count()) if panel._list.item(i).data(Qt.ItemDataRole.UserRole) == "AR3 (6-DOF)")
    panel._on_item_clicked(panel._list.item(ar3_row))
    assert panel._selected_model == "AR3 (6-DOF)"
    print("RobotsCatalogPanel row click updates the selected preview model: PASS")

    # Unchecking a model writes it back through the real HydraConnection and
    # schedules a real push_state() - matches STUDIO's own toggleEnabled().
    item = panel._list.item(ar3_row)
    item.setCheckState(Qt.CheckState.Unchecked)
    loop.run_until_complete(asyncio.sleep(0))
    assert live_state.is_robot_model_enabled("AR3 (6-DOF)") is False
    assert live_state.is_robot_model_enabled("UR5e (6-DOF)") is True, "unchecking one model must not disable another"
    assert push_calls == [True], "unchecking a model must schedule a real push_state()"
    print("RobotsCatalogPanel unchecking a model disables only that model and pushes state: PASS")

    # Manufacturer filter narrows the list without losing enabled state.
    trossen_index = panel._manufacturer_combo.findData("Trossen Robotics")
    assert trossen_index >= 0
    panel._manufacturer_combo.setCurrentIndex(trossen_index)
    expected = [m for m in REAL_ROBOT_MODELS if ROBOT_MANUFACTURERS[m] == "Trossen Robotics"]
    assert panel._list.count() == len(expected) == 2
    all_index = panel._manufacturer_combo.findData("__all__")
    panel._manufacturer_combo.setCurrentIndex(all_index)
    ar3_row_after = next(i for i in range(panel._list.count()) if panel._list.item(i).data(Qt.ItemDataRole.UserRole) == "AR3 (6-DOF)")
    assert panel._list.item(ar3_row_after).checkState() == Qt.CheckState.Unchecked, "the earlier disable must survive a filter round-trip"
    print("RobotsCatalogPanel manufacturer filter narrows the list, preserves enabled state: PASS")

    # DOF filter.
    dof5_index = panel._dof_combo.findData(5)
    panel._dof_combo.setCurrentIndex(dof5_index)
    assert panel._list.count() == len([m for m in REAL_ROBOT_MODELS if robot_model_dof(m) == 5]) == 2
    print("RobotsCatalogPanel DOF filter: PASS")

    loop.close()


if __name__ == "__main__":
    _run()
    print("verify_robots_catalog_panel: all real assertions passed")
