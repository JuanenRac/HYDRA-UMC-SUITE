# =============================================================================
# HYDRA-UMC-SUITE - rack panel refresh verifier
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The rack panel is refreshed on every state push of the server. A push that
# changes nothing about a rack must not reload its 3D preview or recreate its
# slot buttons (that made the panel flicker and ate the focus), while a real
# change to the geometry or to the usable slots must still be shown.
# =============================================================================
import sys

from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, default_rack_system
from hydra_suite.ui.panels.rack_config_panel import RackConfigPanel


def check(label: str, condition: bool) -> None:
    assert condition, label


def state(config: dict) -> HydraState:
    robot = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle", "hasXYTable": True, "rackSystem": config}
    return HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [robot]}]})


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    controller = SuiteController()
    panel = RackConfigPanel(controller)
    group = panel._rack1_widget
    previews: list[dict] = []
    original = group._preview.set_attached_module
    group._preview.set_attached_module = lambda kind, **kw: (previews.append(kw), original(kind, **kw))[1]

    config = default_rack_system()
    config["enabled"] = True
    controller.active_state_changed.emit(state(config))
    check("the first push builds the preview once", len(previews) == 1)
    buttons = list(group._slot_buttons)
    check("the first push builds the slot buttons", len(buttons) == config["rack1"]["capacity"])

    for _ in range(5):
        controller.active_state_changed.emit(state(config))
    check("identical pushes do not reload the preview", len(previews) == 1)
    check("identical pushes keep the very same buttons", group._slot_buttons == buttons and all(a is b for a, b in zip(group._slot_buttons, buttons)))

    changed = default_rack_system()
    changed["enabled"] = True
    changed["rack1"]["usableSlots"][3] = not changed["rack1"]["usableSlots"][3]
    controller.active_state_changed.emit(state(changed))
    check("a changed slot is rebuilt", group._slot_buttons[3].isChecked() == changed["rack1"]["usableSlots"][3])
    check("a changed slot reloads the preview", len(previews) == 2)

    wider = default_rack_system()
    wider["enabled"] = True
    wider["rack1"]["width"] = 300
    controller.active_state_changed.emit(state(wider))
    check("a changed width reloads the preview", len(previews) == 3)
    check("the width is shown", group._dimension_spins["width"].value() == 300)

    moved = default_rack_system()
    moved["enabled"] = True
    moved["rack1"]["width"] = 300
    moved["rack1"]["basePickupPos"]["j1"] = 33.0
    controller.active_state_changed.emit(state(moved))
    check("a moved pickup position is shown", group._pos_spins["j1"].value() == 33.0)
    print("verify_rack_refresh_calm: OK")


if __name__ == "__main__":
    main()
