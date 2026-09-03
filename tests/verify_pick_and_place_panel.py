"""Real assertion-based coverage for PickAndPlacePanel
(ui/panels/pick_and_place_panel.py) - the SUITE-side port of
HYDRA-UMC-STUDIO's own PickAndPlace.tsx. Reuses the
existing, already-tested RobotView.module()/module_enabled()/
set_module() accessors (see verify_module_config_panel.py) rather than
duplicating that coverage - this file focuses on what's new here: the
in-panel Machine switch and the PnP pose-preview fields. Headless: a
real QApplication, no network connection, feeding a real HydraState
through SuiteController.active_state_changed."""
import sys

from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState
from hydra_suite.ui.panels.pick_and_place_panel import PickAndPlacePanel


def _state_with_one_robot() -> HydraState:
    robot: dict = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle"}
    return HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [robot]}]})


def _run() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    controller = SuiteController()
    panel = PickAndPlacePanel(controller)

    controller.active_state_changed.emit(_state_with_one_robot())
    assert panel._machine_type == "juanenPnP", "default machine matches STUDIO's own useState default"
    assert panel._stack.currentIndex() == 0
    print("PickAndPlacePanel empty state, default machine juanenPnP: PASS")

    panel._on_enable()
    module = panel._current_robot.module("juanenPnP")
    assert module["enabled"] is True
    assert panel._stack.currentIndex() == 1
    # isHidden() (this widget's own explicit shown/hidden flag) rather
    # than isVisible() (also gated by every ancestor actually being on
    # screen, which nothing in this headless test - no panel.show() -
    # ever is) - same fix as verify_atc_tools_panel.py's own.
    assert panel._pnp_page.isHidden() is False
    print("PickAndPlacePanel enable juanenPnP -> PnP pose page shown: PASS")

    # Axis edits write into the CORRECT module key.
    panel._on_axis_changed("axisX", 200)
    assert panel._current_robot.module("juanenPnP")["axisX"] == 200
    panel._on_axis_changed("nozzle2Rotation", -90)
    assert panel._current_robot.module("juanenPnP")["nozzle2Rotation"] == -90
    print("PickAndPlacePanel PnP axis edits: PASS")

    # Reset writes size defaults too (even though unused for PnP), plus
    # all 5 axis fields at 0 - matches STUDIO's own handleReset() exactly.
    panel._on_reset()
    module = panel._current_robot.module("juanenPnP")
    assert module["enabled"] is True
    assert module["size"] == {"width": 500, "length": 500}
    assert module["axisX"] == 0 and module["nozzle2Rotation"] == 0
    print("PickAndPlacePanel reset -> size + all axes at defaults: PASS")

    # Switching machine to lumenPnP is a completely separate module key -
    # juanenPnP's own config (just reset) must be untouched.
    panel._machine_combo.setCurrentIndex(panel._machine_combo.findData("lumenPnP"))
    assert panel._machine_type == "lumenPnP"
    assert panel._current_robot.module_enabled("lumenPnP") is False, "lumenPnP starts disabled independently of juanenPnP"
    assert panel._stack.currentIndex() == 0
    assert panel._current_robot.module("juanenPnP")["enabled"] is True, "switching machine must not touch the other module's data"
    print("PickAndPlacePanel machine switch -> independent module keys: PASS")

    panel._on_enable()
    panel._on_axis_changed("axisY", 300)
    assert panel._current_robot.module("lumenPnP")["axisY"] == 300
    assert "axisY" not in panel._current_robot.module("juanenPnP") or panel._current_robot.module("juanenPnP").get("axisY") != 300
    print("PickAndPlacePanel lumenPnP edits stay isolated from juanenPnP: PASS")

    panel._on_disable()
    assert panel._current_robot.module_enabled("lumenPnP") is False
    assert panel._current_robot.module_enabled("juanenPnP") is True, "disabling lumenPnP must not touch juanenPnP"
    print("PickAndPlacePanel disable is per-machine: PASS")

    print("ALL VERIFY_PICK_AND_PLACE_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
