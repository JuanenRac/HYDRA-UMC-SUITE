"""Real assertion-based coverage for PickAndPlacePanel
(ui/panels/pick_and_place_panel.py) - the SUITE-side port of
HYDRA-UMC-STUDIO's own PickAndPlace.tsx. Reuses the
existing, already-tested RobotView.module()/module_enabled()/
set_module() accessors (see verify_module_config_panel.py) rather than
duplicating that coverage - this file focuses on what's new here: the
in-panel Machine switch, the PnP pose-preview fields, and (as of this
pass) the real LumenPnP/JuanenPnP gantry kinematics (render/pnp_rig.py)
and its live 3D preview wiring (RobotViewport.set_attached_pnp()) into
this same panel. Headless: a real QApplication, no network connection,
feeding a real HydraState through SuiteController.active_state_changed."""
import sys

import numpy as np
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState
from hydra_suite.render.kinematics import rot_z, translation
from hydra_suite.render.pnp_rig import PNP_LINK_NAMES, PNP_MESH_DIR, PNP_ROOT, pnp_world_link_transforms
from hydra_suite.render.viewport import RobotViewport
from hydra_suite.ui.panels.pick_and_place_panel import PickAndPlacePanel


def _state_with_one_robot() -> HydraState:
    robot: dict = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle"}
    return HydraState({"activeControllerId": "c1", "controllers": [{"id": "c1", "robots": [robot]}]})


def _run() -> None:
    # QApplication must exist before ANY QWidget (including RobotViewport
    # below) is constructed - built first, before the pure-math checks
    # even though they don't need it themselves, so every check in this
    # file can assume Qt is ready.
    app = QApplication.instance() or QApplication(sys.argv)

    # --- pnp_rig.pnp_world_link_transforms() - real gantry kinematics ---
    # At the zero pose every link's world transform is exactly PNP_ROOT -
    # no carriage has moved off the origin yet.
    zero = pnp_world_link_transforms(0.0, 0.0, 0.0, 0.0, 0.0)
    assert set(zero.keys()) == set(PNP_LINK_NAMES)
    for name in PNP_LINK_NAMES:
        assert np.allclose(zero[name], PNP_ROOT), f"{name} must equal PNP_ROOT at the zero pose"

    # base is a FIXED link - its transform never depends on any axis, even
    # at a real, non-trivial pose.
    posed = pnp_world_link_transforms(433.0, 487.0, 90.0, 90.0, -90.0)
    assert np.allclose(posed["base"], PNP_ROOT), "base must stay fixed regardless of axis values"

    # y_carriage only moves along Y (world, since it's the direct child of
    # the fixed base) - x_carriage/z_carriage_n1/z_carriage_n2 must all
    # inherit that same Y offset (they're downstream in the chain) but
    # y_carriage itself must show zero further X/Z offset of its own.
    y_pos = (np.linalg.inv(PNP_ROOT) @ posed["y_carriage"])[:3, 3]
    assert np.allclose(y_pos, [0.0, 0.487, 0.0], atol=1e-9), "y_carriage must translate exactly (0, axisY, 0) in its own parent frame"

    # x_carriage adds its own local X on top of y_carriage's Y - both
    # offsets must be present together, not one overwriting the other.
    x_pos = (np.linalg.inv(PNP_ROOT) @ posed["x_carriage"])[:3, 3]
    assert np.allclose(x_pos, [0.433, 0.487, 0.0], atol=1e-9), "x_carriage must carry both its own X and its parent y_carriage's Y"

    # z_carriage_n1/n2 share the exact same real position (same Z travel,
    # same parent x_carriage) - they differ ONLY in rotation, matching
    # LumenPnPRig.tsx's own two sibling groups at the same [0,0,z] offset.
    n1_pos = (np.linalg.inv(PNP_ROOT) @ posed["z_carriage_n1"])[:3, 3]
    n2_pos = (np.linalg.inv(PNP_ROOT) @ posed["z_carriage_n2"])[:3, 3]
    assert np.allclose(n1_pos, [0.433, 0.487, 0.09], atol=1e-9)
    assert np.allclose(n2_pos, n1_pos, atol=1e-9), "both nozzles share the same real position - only their rotation differs"
    z_n1_parent = posed["x_carriage"] @ translation((0.0, 0.0, 0.09))
    n1_rot = (np.linalg.inv(z_n1_parent) @ posed["z_carriage_n1"])[:3, :3]
    assert np.allclose(n1_rot, rot_z(np.pi / 2)[:3, :3], atol=1e-9), "nozzle1's own local rotation must be exactly rot_z(nozzle1_deg)"
    print("pnp_rig.pnp_world_link_transforms(): real gantry chain composition PASS")

    # --- RobotViewport.set_attached_pnp() pending-mesh-load cache path -
    # headless, so _gl_ready is never True and no real GL buffer/STL load
    # happens here; this exercises the same pending-rebuild pattern
    # set_attached_module() already has, now for the real-mesh PnP path. -
    pnp_viewport = RobotViewport()
    assert pnp_viewport._renderer._pnp_machine_type is None
    pnp_viewport.set_attached_pnp("lumenPnP", axis_x_mm=100.0, axis_y_mm=200.0, axis_z_mm=30.0, nozzle1_deg=45.0, nozzle2_deg=-45.0)
    assert pnp_viewport._renderer._pnp_machine_type == "lumenPnP"
    assert pnp_viewport._renderer._pnp_pose == (100.0, 200.0, 30.0, 45.0, -45.0)
    assert pnp_viewport._renderer._pending_pnp_mesh_load is True, "GL not ready yet - the real mesh load must be deferred, not lost"
    assert PNP_MESH_DIR not in pnp_viewport._renderer._mesh_buffers_by_dir
    pnp_viewport.set_attached_pnp(None)
    assert pnp_viewport._renderer._pnp_machine_type is None
    print("RobotViewport.set_attached_pnp() pending-mesh-load cache path: PASS")

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
    assert panel._pnp_viewport._renderer._pnp_machine_type == "juanenPnP", "enabling must attach the live 3D preview to the real machine key"
    print("PickAndPlacePanel enable juanenPnP -> PnP pose page shown: PASS")

    # Axis edits write into the CORRECT module key AND update the live 3D
    # preview immediately (not only once the server echoes the write
    # back) - the real gap fixed in this same pass alongside
    # module_config_panel.py's own _on_size_changed().
    panel._on_axis_changed("axisX", 200)
    assert panel._current_robot.module("juanenPnP")["axisX"] == 200
    assert panel._pnp_viewport._renderer._pnp_pose[0] == 200.0, "the embedded viewport must reflect the new axisX immediately"
    panel._on_axis_changed("nozzle2Rotation", -90)
    assert panel._current_robot.module("juanenPnP")["nozzle2Rotation"] == -90
    assert panel._pnp_viewport._renderer._pnp_pose[4] == -90.0
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
    assert panel._pnp_viewport._renderer._pnp_machine_type is None, "lumenPnP starts disabled - the preview must detach, not keep showing juanenPnP's own pose"
    print("PickAndPlacePanel machine switch -> independent module keys: PASS")

    panel._on_enable()
    assert panel._pnp_viewport._renderer._pnp_machine_type == "lumenPnP", "enabling lumenPnP must attach the preview to THIS machine key, not juanenPnP"
    panel._on_axis_changed("axisY", 300)
    assert panel._current_robot.module("lumenPnP")["axisY"] == 300
    assert "axisY" not in panel._current_robot.module("juanenPnP") or panel._current_robot.module("juanenPnP").get("axisY") != 300
    assert panel._pnp_viewport._renderer._pnp_pose[1] == 300.0
    print("PickAndPlacePanel lumenPnP edits stay isolated from juanenPnP: PASS")

    panel._on_disable()
    assert panel._current_robot.module_enabled("lumenPnP") is False
    assert panel._current_robot.module_enabled("juanenPnP") is True, "disabling lumenPnP must not touch juanenPnP"
    assert panel._pnp_viewport._renderer._pnp_machine_type is None, "disabling the active machine must detach the preview"
    print("PickAndPlacePanel disable is per-machine: PASS")

    print("ALL VERIFY_PICK_AND_PLACE_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
