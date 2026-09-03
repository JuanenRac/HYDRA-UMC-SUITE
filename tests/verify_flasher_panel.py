"""Real assertion-based coverage for FlasherPanel
(ui/panels/flasher_panel.py) - the SUITE-side port of
HYDRA-UMC-STUDIO's own Flasher.tsx (2026-09-03). Exercises real
can_ota.py logic (mock_flash actually runs to completion, real CRC32),
not stubbed. Headless: a real QApplication, no network connection,
feeding a real HydraState through SuiteController.active_state_changed."""
import asyncio
import sys

from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState
from hydra_suite.ui.panels.flasher_panel import HYDRA_BRAIN_TIERS, URTC_TIERS, FlasherPanel


def _state_with_robots() -> HydraState:
    return HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [
                {
                    "id": "c1",
                    "name": "HYDRA-UMC Master",
                    "kinematicBrain": {"firmwareVersion": "0.9.0", "bootloaderVersion": "0.0.0", "hardwareId": "KB-001"},
                    "robots": [
                        {"id": "1", "model": "Parol6", "urtcConnected": True, "urtcHead": {"expansionBoardType": 3}},
                        {"id": "2", "model": "Faze4", "urtcConnected": False},
                    ],
                }
            ],
        }
    )


def _run() -> None:
    app = QApplication.instance() or QApplication(sys.argv)

    # --- URTC_TIERS instance (urtcHead/urtcExpansion, per-robot) ------------
    controller = SuiteController()
    panel = FlasherPanel(controller, tiers=URTC_TIERS)
    controller.active_state_changed.emit(_state_with_robots())

    assert panel._tier == "urtcHead", "URTC instance defaults to its own first tier"
    assert panel._robot_combo.count() == 2
    assert panel._robot_id == "1"
    # Robot 1 has urtcConnected=True and expansionBoardType=3 -> both tier options enabled.
    assert panel._tier_combo.model().item(0).isEnabled() is True   # urtcHead
    assert panel._tier_combo.model().item(1).isEnabled() is True   # urtcExpansion (type 3 = Advanced)
    print("FlasherPanel URTC instance: robot combo + tier gating (robot with expansion): PASS")

    # Switch to robot 2 (urtcConnected=False, no urtcHead block at all) -
    # both tier options must now be disabled.
    panel._robot_combo.setCurrentIndex(1)
    assert panel._robot_id == "2"
    assert panel._tier_combo.model().item(0).isEnabled() is False, "urtcHead must be disabled - robot 2 has urtcConnected=False"
    assert panel._tier_combo.model().item(1).isEnabled() is False, "urtcExpansion must be disabled - no expansion board"
    print("FlasherPanel URTC instance: tier gating (robot without URTC/expansion): PASS")

    # --- HYDRA_BRAIN_TIERS instance (kinematicBrain/controllerBoard) -------
    controller2 = SuiteController()
    panel2 = FlasherPanel(controller2, tiers=HYDRA_BRAIN_TIERS)
    controller2.active_state_changed.emit(_state_with_robots())

    assert panel2._tier == "kinematicBrain"
    # isHidden() (this widget's own explicit shown/hidden flag), not
    # isVisible() (also gated by every ancestor being on screen, never
    # true headless) - same fix as every other panel's own verify script.
    assert panel2._robot_combo.isHidden() is True, "kinematicBrain needs no robot slot"
    target = panel2._current_target()
    assert target is not None and target.robot_id is None
    assert "SPI" in panel2._hop_label.text() and "Kinematic Brain" in panel2._hop_label.text()
    # kinematicBrain board state was pre-seeded in the fixture.
    assert "0.9.0" in panel2._version_label.text()
    print("FlasherPanel HYDRA_BRAIN instance: kinematicBrain target + real board state display: PASS")

    panel2._tier_combo.setCurrentIndex(panel2._tier_combo.findData("controllerBoard"))
    assert panel2._robot_combo.isHidden() is False, "controllerBoard needs a robot slot"
    target2 = panel2._current_target()
    assert target2 is not None and target2.robot_index0 == 0
    print("FlasherPanel HYDRA_BRAIN instance: controllerBoard needs robot slot: PASS")

    # --- Real mock flash cycle end to end, via the panel's own real path ---
    panel2._set_file("g474_application.bin", bytes(6000))  # -> ceil(6000/2048) = 3 pages
    assert panel2._flash_btn.isEnabled() is True
    asyncio.run(panel2._do_flash())
    assert panel2._progress_bar.value() == 100
    assert "0.0.0" not in panel2._board_state().get("firmwareVersion", "")  # just sanity, real assertion below
    assert panel2._board_state().get("firmwareVersion") == "g474_application"
    assert "Done" in panel2._log_view.toPlainText() or "complete" in panel2._log_view.toPlainText().lower()
    print("FlasherPanel real mock_flash cycle end to end, board state patched after: PASS")

    print("ALL VERIFY_FLASHER_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
