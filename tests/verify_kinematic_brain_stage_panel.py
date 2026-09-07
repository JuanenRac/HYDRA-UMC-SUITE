"""Real assertion-based coverage for ControllerView.kinematic_brain_stage/
set_kinematic_brain_stage (models.py) and KinematicBrainStagePanel
(ui/panels/kinematic_brain_stage_panel.py) - the SUITE-side port of
HYDRA-UMC-STUDIO's own KinematicBrainStage.tsx. UNLIKE every
panel tested so far, this is CONTROLLER-level state, not per-robot -
no robot selector, no per-robot lookup. Headless: a real QApplication,
no network connection, feeding a real HydraState through
SuiteController.active_state_changed."""
import sys

from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import ControllerView, HydraState, default_kinematic_brain_stage
from hydra_suite.ui.panels.kinematic_brain_stage_panel import KinematicBrainStagePanel


def _state_with_stage(stage: dict | None = None) -> HydraState:
    controller: dict = {"id": "c1", "robots": []}
    if stage is not None:
        controller["kinematicBrainStage"] = stage
    return HydraState({"activeControllerId": "c1", "controllers": [controller]})


def _run() -> None:
    # --- ControllerView.kinematic_brain_stage/set_kinematic_brain_stage ----
    controller_view = ControllerView({"id": "c1"})
    default = controller_view.kinematic_brain_stage
    assert default["atcRevolver"]["toolCount"] == 6, "missing field must read as the real seed default"
    assert "kinematicBrainStage" not in controller_view.raw, "reading a missing field must not silently write it back"

    stage = default_kinematic_brain_stage()
    stage["heatedBed"]["targetTemp"] = 80
    controller_view.set_kinematic_brain_stage(stage)
    assert controller_view.kinematic_brain_stage["heatedBed"]["targetTemp"] == 80
    print("ControllerView.kinematic_brain_stage/set_kinematic_brain_stage: PASS")

    # --- KinematicBrainStagePanel, headless, real Qt widgets ---------------
    app = QApplication.instance() or QApplication(sys.argv)
    controller = SuiteController()
    panel = KinematicBrainStagePanel(controller)

    controller.active_state_changed.emit(_state_with_stage())
    assert panel._axis_labels["x"].text() == "0.00"
    assert panel._width_spin.value() == 600, "real seed default table width"
    print("KinematicBrainStagePanel initial state from real seed default: PASS")

    # Jog X by the default 10mm step, clamped to table width (600mm).
    panel._on_jog("x", 1)
    active = panel._active_controller
    assert active.kinematic_brain_stage["xyTable"]["x"] == 10.0
    for _ in range(70):
        panel._on_jog("x", 1)
    assert active.kinematic_brain_stage["xyTable"]["x"] == 600.0, "jog must clamp to tableSize.width"
    print("KinematicBrainStagePanel XY gantry jog + clamp: PASS")

    # Heated bed target temp + SSR toggle.
    panel._on_target_temp_changed(90)
    assert active.kinematic_brain_stage["heatedBed"]["targetTemp"] == 90
    panel._on_ssr_toggle()
    assert active.kinematic_brain_stage["heatedBed"]["ssrActive"] is True
    print("KinematicBrainStagePanel heated bed: PASS")

    # ATC revolver step wraps around toolCount (default 6) and sets homed.
    assert active.kinematic_brain_stage["atcRevolver"]["homed"] is False
    panel._on_atc_step(-1)
    atc = active.kinematic_brain_stage["atcRevolver"]
    assert atc["currentIndex"] == 5, "stepping back from index 0 with 6 slots must wrap to 5"
    assert atc["homed"] is True
    print("KinematicBrainStagePanel ATC revolver step + wrap + homed: PASS")

    # Conveyor: starts not installed, Mark as installed, then run + speed.
    assert active.kinematic_brain_stage["conveyor"]["installed"] is False
    panel._on_conveyor_install()
    assert active.kinematic_brain_stage["conveyor"]["installed"] is True
    panel._on_conveyor_run_toggle()
    assert active.kinematic_brain_stage["conveyor"]["running"] is True
    panel._on_conveyor_speed_changed(75)
    assert active.kinematic_brain_stage["conveyor"]["speedPercent"] == 75
    print("KinematicBrainStagePanel conveyor install/run/speed: PASS")

    # Endstops, fans, pumps, valves toggle independently.
    panel._on_endstop_toggle("xMin")
    assert active.kinematic_brain_stage["endstops"]["xMin"] is True
    panel._on_fan_toggle(1)
    assert active.kinematic_brain_stage["fans"][1] is True
    assert active.kinematic_brain_stage["fans"][0] is False
    panel._on_pump_toggle(9)
    assert active.kinematic_brain_stage["pumps"][9] is True
    panel._on_valve_toggle(0)
    assert active.kinematic_brain_stage["valves"][0] is True
    print("KinematicBrainStagePanel endstops/fans/pumps/valves: PASS")

    print("ALL VERIFY_KINEMATIC_BRAIN_STAGE_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
