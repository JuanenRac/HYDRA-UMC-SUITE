"""Real assertion-based coverage for RobotView.rack_system/set_rack_system
(models.py) and RackConfigPanel (ui/panels/rack_config_panel.py) - the
SUITE-side port of HYDRA-UMC-STUDIO's own RackConfigView.tsx.
Headless: a real QApplication, no network connection, feeding a real
HydraState through SuiteController.active_state_changed. Same convention
as verify_xy_table_panel.py."""
import sys

from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, RobotView, default_rack_system
from hydra_suite.ui.panels.rack_config_panel import RackConfigPanel


def _state_with_one_robot(rack_system: dict | None = None) -> HydraState:
    robot: dict = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle", "hasXYTable": True}
    if rack_system is not None:
        robot["rackSystem"] = rack_system
    return HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [robot]}]})


def _run() -> None:
    # --- RobotView.rack_system/set_rack_system ------------------------------
    robot = RobotView({"id": 1})
    default = robot.rack_system
    assert default["enabled"] is False, "missing rackSystem must read as the real seed default, disabled"
    assert default["rack1"]["type"] == "Input"
    assert default["rack2"]["type"] == "Output"
    assert "rackSystem" not in robot.raw, "reading a missing field must not silently write it back"

    config = default_rack_system()
    config["enabled"] = True
    robot.set_rack_system(config)
    assert robot.rack_system["enabled"] is True
    assert robot.raw["rackSystem"]["rack1"]["capacity"] == 24
    print("RobotView.rack_system/set_rack_system: PASS")

    # --- RackConfigPanel, headless, real Qt widgets -------------------------
    app = QApplication.instance() or QApplication(sys.argv)
    controller = SuiteController()
    panel = RackConfigPanel(controller)

    # Disabled by default - empty-state page.
    controller.active_state_changed.emit(_state_with_one_robot())
    assert panel._stack.currentIndex() == 0
    assert panel._current_robot is not None
    print("RackConfigPanel empty state: PASS")

    panel._on_enable()
    assert panel._current_robot.rack_system["enabled"] is True
    assert panel._stack.currentIndex() == 1
    print("RackConfigPanel enable: PASS")

    # Type change on rack1.
    panel._on_field_changed("rack1", "type", "None")
    assert panel._current_robot.rack_system["rack1"]["type"] == "None"
    panel._on_field_changed("rack1", "type", "Input")
    assert panel._current_robot.rack_system["rack1"]["type"] == "Input"

    # Capacity + slot toggle on rack2.
    panel._on_field_changed("rack2", "capacity", 6)
    assert panel._current_robot.rack_system["rack2"]["capacity"] == 6
    panel._on_slot_toggle("rack2", 2)
    assert panel._current_robot.rack_system["rack2"]["usableSlots"][2] is False, "slot 2 starts usable (default True) -> toggle flips it off"
    panel._on_slot_toggle("rack2", 2)
    assert panel._current_robot.rack_system["rack2"]["usableSlots"][2] is True

    # Slot toggle beyond the original array length pads and sets True
    # (matches STUDIO's own `!undefined -> true` real behavior).
    panel._on_field_changed("rack1", "capacity", 24)
    assert len(panel._current_robot.rack_system["rack1"]["usableSlots"]) == 24
    print("RackConfigPanel type/capacity/slot edits: PASS")

    # Base pickup position, including the table tx/ty fields.
    panel._on_field_changed("rack1", "basePickupPos.j1", 45.0)
    assert panel._current_robot.rack_system["rack1"]["basePickupPos"]["j1"] == 45.0
    panel._on_field_changed("rack1", "basePickupPos.tx", 12.5)
    assert panel._current_robot.rack_system["rack1"]["basePickupPos"]["tx"] == 12.5
    print("RackConfigPanel base pickup position edits: PASS")

    # Reset resets BOTH racks regardless of which one's button fired -
    # the real STUDIO quirk this panel deliberately reproduces.
    panel._on_reset()
    config = panel._current_robot.rack_system
    assert config["enabled"] is True
    assert config["rack1"] == default_rack_system()["rack1"]
    assert config["rack2"] == default_rack_system()["rack2"]
    print("RackConfigPanel reset -> both racks reset together: PASS")

    # Disable clears only the flag.
    panel._on_disable()
    assert panel._current_robot.rack_system["enabled"] is False
    assert panel._stack.currentIndex() == 0
    print("RackConfigPanel disable: PASS")

    print("ALL VERIFY_RACK_CONFIG_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
