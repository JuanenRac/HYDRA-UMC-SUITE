"""Real assertion-based coverage for RobotView's new generic module
accessors (models.py) and ModuleConfigPanel (ui/panels/module_config_panel.py,
the shared implementation behind CncPanel/LaserPanel/HeatedBedPanel - see
that file's own header for why one class covers all three). Headless: a
real QApplication + qasync loop, no network connection, feeding a real
HydraState through SuiteController.active_state_changed the same way a
real WS/REST update would - not mocked at the Qt layer, only the network
is never actually opened."""
import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, RobotView
from hydra_suite.ui.panels.cnc_panel import CncPanel
from hydra_suite.ui.panels.heated_bed_panel import HeatedBedPanel
from hydra_suite.ui.panels.laser_panel import LaserPanel


def _state_with_one_robot(cnc: dict | None = None) -> HydraState:
    robot: dict = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle"}
    if cnc is not None:
        robot["juanenCNC"] = cnc
    return HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [{"id": "c1", "robots": [robot]}],
        }
    )


def _state_with_heated_bed(heated_bed: dict | None = None) -> HydraState:
    robot: dict = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle"}
    if heated_bed is not None:
        robot["heatedBed"] = heated_bed
    return HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [{"id": "c1", "robots": [robot]}],
        }
    )


def _run() -> None:
    # --- RobotView.module()/module_enabled()/set_module() -----------------
    robot = RobotView({"id": 1})
    assert robot.module("juanenCNC") == {}, "module() must return {} when absent, never None/KeyError"
    assert robot.module_enabled("juanenCNC") is False

    robot.set_module("juanenCNC", {"enabled": True, "size": {"width": 500, "length": 500}})
    assert robot.module_enabled("juanenCNC") is True
    assert robot.module("juanenCNC")["size"]["width"] == 500
    print("RobotView.module()/module_enabled()/set_module(): PASS")

    # --- ModuleConfigPanel, headless, real Qt widgets ----------------------
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = SuiteController()
    panel = CncPanel(controller)

    # No robots at all yet - the empty-state page, nothing enabled.
    controller.active_state_changed.emit(_state_with_one_robot(cnc=None))
    assert panel._stack.currentIndex() == 0, "no juanenCNC block yet -> empty-state page"
    assert panel._current_robot is not None

    # Real enable click - mutates the robot's own raw dict and switches page.
    panel._on_enable()
    assert panel._current_robot.module_enabled("juanenCNC") is True
    assert panel._stack.currentIndex() == 1, "enabling must switch to the settings page"
    assert panel._width_spin.value() == 500
    assert panel._length_spin.value() == 500

    # A real width change writes back into the same robot's raw dict.
    panel._width_spin.setValue(750)
    assert panel._current_robot.module("juanenCNC")["size"]["width"] == 750

    # Remove Module really disables it and switches back to the empty page.
    panel._on_disable()
    assert panel._current_robot.module_enabled("juanenCNC") is False
    assert panel._stack.currentIndex() == 0

    # Reset re-enables with the documented defaults (matches CNC.tsx's own
    # handleReset()).
    panel._on_reset()
    module = panel._current_robot.module("juanenCNC")
    assert module["enabled"] is True
    assert module["size"] == {"width": 500, "length": 500}
    assert module["worldPos"] == {"x": 0, "y": 0}
    print("CncPanel enable/size-change/disable/reset round-trip: PASS")

    # A state that already has the module enabled loads straight into the
    # settings page - not the empty state first.
    laser_panel = LaserPanel(controller)
    controller.active_state_changed.emit(
        _state_with_one_robot(cnc={"enabled": True, "size": {"width": 300, "length": 400}})
    )
    # laser_panel reads juanenLaser, not juanenCNC - still absent, so it
    # must stay on the empty-state page even though juanenCNC is present.
    assert laser_panel._stack.currentIndex() == 0, "juanenLaser is absent - must not react to juanenCNC's own data"
    print("LaserPanel reads its own module key independently of CncPanel: PASS")

    # --- HeatedBedPanel - extra heating controls beyond shared size/reset --
    heated_bed_panel = HeatedBedPanel(controller)
    controller.active_state_changed.emit(_state_with_heated_bed(heated_bed=None))
    assert heated_bed_panel._stack.currentIndex() == 0, "no heatedBed block yet -> empty-state page"

    # Enable sets the documented extra defaults (matches HeatedBedConfig.tsx's
    # own handleReset() values, applied here via setdefault on first enable).
    heated_bed_panel._on_enable()
    module = heated_bed_panel._current_robot.module("heatedBed")
    assert module["targetTemp"] == 60
    assert module["currentTemp1"] == 25.0
    assert module["currentTemp2"] == 25.0
    assert module["ssrActive"] is False
    assert heated_bed_panel._target_spin.value() == 60
    assert heated_bed_panel._ssr_btn.isChecked() is False
    assert heated_bed_panel._temp1_label.text() == "25.0 °C"
    print("HeatedBedPanel enable defaults: PASS")

    # A real target-temp change writes back into the module dict.
    heated_bed_panel._target_spin.setValue(85)
    assert heated_bed_panel._current_robot.module("heatedBed")["targetTemp"] == 85

    # A real SSR toggle writes back too, and the label follows the state.
    heated_bed_panel._ssr_btn.setChecked(True)
    assert heated_bed_panel._current_robot.module("heatedBed")["ssrActive"] is True
    assert heated_bed_panel._ssr_btn.text() == "SSR ON"
    print("HeatedBedPanel target-temp/SSR write-back: PASS")

    # Reset re-enables with the documented defaults, including the extra
    # heating fields (matches HeatedBedConfig.tsx's own handleReset()).
    heated_bed_panel._on_reset()
    module = heated_bed_panel._current_robot.module("heatedBed")
    assert module["enabled"] is True
    assert module["targetTemp"] == 60
    assert module["currentTemp1"] == 25.0
    assert module["ssrActive"] is False
    print("HeatedBedPanel reset includes extra heating fields: PASS")

    # A state that already has real live telemetry (a value NOT among the
    # defaults) renders the real numbers, not the fallback.
    controller.active_state_changed.emit(
        _state_with_heated_bed(heated_bed={"enabled": True, "size": {"width": 500, "length": 500}, "targetTemp": 70, "currentTemp1": 68.3, "currentTemp2": 67.9, "ssrActive": True})
    )
    assert heated_bed_panel._target_spin.value() == 70
    assert heated_bed_panel._temp1_label.text() == "68.3 °C"
    assert heated_bed_panel._temp2_label.text() == "67.9 °C"
    assert heated_bed_panel._ssr_btn.isChecked() is True
    print("HeatedBedPanel renders real live telemetry from state: PASS")

    print("ALL VERIFY_MODULE_CONFIG_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
