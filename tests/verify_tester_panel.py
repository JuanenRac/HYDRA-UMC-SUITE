"""Real assertion-based coverage for TesterPanel
(ui/panels/tester_panel.py) - the SUITE-side port of
HYDRA-UMC-STUDIO's own Tester.tsx, the LAST of the 11
[[project_suite_studio_parity_gap]] panels. Exercises real
can_ota.py logic (mock_self_test/mock_bus_monitor actually run, not
stubbed). Headless: a real QApplication, no network connection, feeding
a real HydraState through SuiteController.active_state_changed."""
import asyncio
import sys

from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState
from hydra_suite.ui.panels.flasher_panel import HYDRA_BRAIN_TIERS, URTC_TIERS
from hydra_suite.ui.panels.tester_panel import TesterPanel, _category_for


def _state_with_robots() -> HydraState:
    return HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [
                {
                    "id": "c1",
                    "name": "HYDRA-UMC Master",
                    "robots": [
                        {"id": "1", "model": "Parol6", "tool": "Soldering Station (T12)", "urtcConnected": True, "urtcHead": {"expansionBoardType": 4}},
                        {"id": "2", "model": "Faze4", "tool": "Vacuum / Pneumatic Gripper", "urtcConnected": False},
                    ],
                }
            ],
        }
    )


def _run() -> None:
    # --- _category_for - real per-tool category mapping ---------------------
    assert _category_for("Soldering Station (T12)") == "thermal"
    assert _category_for("Drill (BL4260)") == "motor"
    assert _category_for("Vacuum / Pneumatic Gripper") == "vacuum"
    assert _category_for("Spot Welder Head") == "binary"
    assert _category_for("AOI (Automated Optical Inspection) System") == "generic"
    print("_category_for real per-tool mapping: PASS")

    app = QApplication.instance() or QApplication(sys.argv)

    # --- URTC_TIERS instance -------------------------------------------
    controller = SuiteController()
    panel = TesterPanel(controller, tiers=URTC_TIERS)
    controller.active_state_changed.emit(_state_with_robots())

    assert panel._tier == "urtcHead"
    # isHidden() not isVisible() - same headless-test gotcha as every
    # other panel's own verify script.
    assert panel._global_box.isHidden() is False, "Global Controls only shown for urtcHead"
    assert panel._fram_box.isHidden() is False, "F-RAM shown for urtcHead too"
    assert panel._telemetry_box.isHidden() is False
    print("TesterPanel URTC instance: urtcHead shows Global Controls/F-RAM/Telemetry: PASS")

    panel._robot_combo.setCurrentIndex(1)  # robot 2: no URTC, no expansion
    assert panel._tier_combo.model().item(0).isEnabled() is False  # urtcHead disabled
    assert panel._tier_combo.model().item(1).isEnabled() is False  # urtcExpansion disabled
    print("TesterPanel URTC instance: per-option tier gating (robot without URTC): PASS")

    # --- Global controls - real local state, not persisted -----------------
    panel._robot_combo.setCurrentIndex(0)
    assert panel._ring_on is False
    panel._on_toggle_ring()
    assert panel._ring_on is True
    panel._status_color = "#ff0000"
    panel._refresh_target_controls()
    assert "#ff0000" in panel._status_led_btn.styleSheet()
    print("TesterPanel Global Controls: real local UI state: PASS")

    # --- F-RAM erase - real local state --------------------------------
    panel._on_fram_erase()
    assert panel._fram_state is False
    print("TesterPanel F-RAM erase: PASS")

    # --- Real mock self-test, full run through the panel's own path --------
    async def _selftest():
        await panel._do_self_test()
    asyncio.run(_selftest())
    assert panel._testing is False
    assert len(panel._self_test_labels) > 0
    print(f"TesterPanel real mock_self_test run: {len(panel._self_test_labels)} steps rendered: PASS")

    # --- Real mock bus monitor - start, let it emit a frame, stop ---------
    async def _monitor():
        panel._on_toggle_monitor()
        assert panel._monitor_task is not None
        await asyncio.sleep(0.5)  # real generator's own first frame lands ~0.2s in
        assert len(panel._frames) > 0, "real mock_bus_monitor must have emitted at least one frame by now"
        panel._on_toggle_monitor()  # stop
        assert panel._monitor_task is None
        frame_count_after_stop = len(panel._frames)
        await asyncio.sleep(0.3)
        assert len(panel._frames) == frame_count_after_stop, "stopping must actually cancel the task, not just hide the button state"
    asyncio.run(_monitor())
    print("TesterPanel real mock_bus_monitor start/stop, real cancellation: PASS")

    # --- HYDRA_BRAIN_TIERS instance - kinematicBrain has no robot slot -----
    controller2 = SuiteController()
    panel2 = TesterPanel(controller2, tiers=HYDRA_BRAIN_TIERS)
    controller2.active_state_changed.emit(_state_with_robots())
    assert panel2._tier == "kinematicBrain"
    assert panel2._robot_combo.isHidden() is True
    assert panel2._global_box.isHidden() is True, "Global Controls is urtcHead-only, never shown for kinematicBrain"
    assert panel2._fram_box.isHidden() is True, "F-RAM is controllerBoard/urtcHead-only"
    print("TesterPanel HYDRA_BRAIN instance: kinematicBrain hides robot-scoped sections: PASS")

    print("ALL VERIFY_TESTER_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
