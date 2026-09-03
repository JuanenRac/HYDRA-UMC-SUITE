"""Real assertion-based coverage for RobotView.xy_table/set_xy_table/
set_has_xy_table (models.py) and XYTablePanel (ui/panels/xy_table_panel.py) -
the SUITE-side port of HYDRA-UMC-STUDIO's own XYTableConfig.tsx
(2026-09-03). Headless: a real QApplication, no network connection,
feeding a real HydraState through SuiteController.active_state_changed
the same way a real WS/REST update would. Same convention as
verify_atc_tools_panel.py."""
import sys

from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, RobotView
from hydra_suite.ui.panels.xy_table_panel import XYTablePanel, _DISPLAY_DEFAULT_SIZE_MM, _RESET_SIZE_MM


def _state_with_one_robot(has_xy_table: bool = False, xy_table: dict | None = None) -> HydraState:
    robot: dict = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle", "hasXYTable": has_xy_table}
    if xy_table is not None:
        robot["xyTable"] = xy_table
    return HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [robot]}]})


def _run() -> None:
    # --- RobotView.xy_table/set_xy_table/set_has_xy_table ------------------
    robot = RobotView({"id": 1})
    assert robot.has_xy_table is False
    assert robot.xy_table is None

    robot.set_has_xy_table(True)
    assert robot.has_xy_table is True
    assert robot.xy_table is None, "matches STUDIO's own handleAddTable() - flag only, no xyTable block yet"

    robot.set_xy_table({"pos": {"x": 1, "y": 2}, "tableSize": {"width": 300, "length": 300}})
    assert robot.xy_table is not None
    assert robot.xy_table["pos"]["x"] == 1

    robot.set_xy_table(None)
    assert robot.xy_table is None
    assert "xyTable" not in robot.raw
    print("RobotView.xy_table/set_xy_table/set_has_xy_table: PASS")

    # --- XYTablePanel, headless, real Qt widgets ----------------------------
    app = QApplication.instance() or QApplication(sys.argv)
    controller = SuiteController()
    panel = XYTablePanel(controller)

    # No XY table yet - empty-state page.
    controller.active_state_changed.emit(_state_with_one_robot(has_xy_table=False))
    assert panel._stack.currentIndex() == 0
    assert panel._current_robot is not None
    print("XYTablePanel empty state: PASS")

    # Enable writes only the flag, matching STUDIO's handleAddTable().
    panel._on_enable()
    assert panel._current_robot.has_xy_table is True
    assert panel._current_robot.xy_table is None
    assert panel._stack.currentIndex() == 1
    # Display fallback shows 500mm even with no real xyTable object yet.
    assert panel._width_spin.value() == _DISPLAY_DEFAULT_SIZE_MM
    print("XYTablePanel enable -> flag only, display fallback 500mm: PASS")

    # Jog/size no-op until a real xyTable object exists (faithful port of
    # STUDIO's own real quirk - see xy_table_panel.py's own header).
    panel._on_width_changed(400)
    assert panel._current_robot.xy_table is None, "size change must no-op with no real xyTable yet"
    panel._on_jog("x", 1)
    assert panel._current_robot.xy_table is None, "jog must no-op with no real xyTable yet"
    print("XYTablePanel size/jog no-op before Reset: PASS")

    # Reset creates the real object, at the RESET default (300mm), not
    # the display default (500mm) - the two deliberately differ.
    panel._on_reset()
    table = panel._current_robot.xy_table
    assert table is not None
    assert table["tableSize"]["width"] == _RESET_SIZE_MM == 300
    assert table["pos"] == {"x": 0, "y": 0}
    print("XYTablePanel reset -> real xyTable at 300mm reset default: PASS")

    # Now size/jog actually write.
    panel._on_width_changed(450)
    assert panel._current_robot.xy_table["tableSize"]["width"] == 450

    panel._step_combo.setCurrentIndex(panel._step_combo.findData(10.0))
    panel._on_jog("x", 1)
    assert panel._current_robot.xy_table["pos"]["x"] == 10.0
    panel._on_jog("x", 1)
    assert panel._current_robot.xy_table["pos"]["x"] == 20.0

    # Jog clamps to table bounds.
    panel._current_robot.xy_table["pos"]["x"] = 445
    panel._on_jog("x", 1)  # +10 would overshoot the 450mm width
    assert panel._current_robot.xy_table["pos"]["x"] == 450.0, "jog must clamp to tableSize.width"
    print("XYTablePanel size/jog after reset, with clamping: PASS")

    # Disable only clears the flag, matching STUDIO exactly (xyTable data
    # itself is left in place, same as `updateRobot(id, {hasXYTable:
    # false})` never touching the xyTable key).
    panel._on_disable()
    assert panel._current_robot.has_xy_table is False
    assert panel._current_robot.xy_table is not None, "disable must not clear the xyTable data itself"
    assert panel._stack.currentIndex() == 0
    print("XYTablePanel disable -> flag cleared, data kept, empty-state page: PASS")

    print("ALL VERIFY_XY_TABLE_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
