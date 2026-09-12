# =============================================================================
# HYDRA-UMC-SUITE - Independent machine asset and renderer dispatch checks
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from hydra_suite.render.pnp_rig import MACHINE_MESH_DIRS, machine_mesh_dir, PNP_ALL_MESH_FILES
from hydra_suite.render.mesh import load_link_set
from hydra_suite.render.viewport import ASSETS_DIR, RobotViewport


def main():
    assert len(set(MACHINE_MESH_DIRS.values())) == 4
    for machine, directory in MACHINE_MESH_DIRS.items():
        assert machine_mesh_dir(machine) == directory
        assert (ASSETS_DIR/directory/"ATTRIBUTION.txt").is_file()
        meshes=load_link_set(ASSETS_DIR/directory, PNP_ALL_MESH_FILES)
        assert len(meshes) == 167
        assert all(m.vertices.size and np.isfinite(m.vertices).all() for m in meshes.values())
    try:
        machine_mesh_dir("../lumenpnp")
        raise AssertionError("Unknown machine must not fall back")
    except ValueError:
        pass
    app=QApplication.instance() or QApplication([])
    view=RobotViewport()
    for machine in MACHINE_MESH_DIRS:
        if machine in ("juanenCNC","juanenLaser"):
            view.set_attached_module(machine)
        else:
            view.set_attached_pnp(machine, 10, 20, 5, 30, 40)
        assert view._renderer._pnp_machine_type == machine
        assert view._renderer._pending_pnp_mesh_load
    view.set_attached_module("heatedBed",100,100)
    assert view._renderer._pnp_machine_type is None
    assert view._renderer._attached_module_type == "heatedBed"
    view.close()
    print("VERIFY_MACHINE_ASSETS=PASS roots=4 meshes=668 dispatch=PASS")


if __name__ == "__main__":
    main()
