"""LumenPnP: 160 real static CAD parts wired into render/pnp_rig.py +
render/viewport.py - mirrors HYDRA-UMC-STUDIO's own
LumenPnPRig.tsx batches 1-5, closing the "SUITE has the data but
pnp_rig.py never loads it" gap those STUDIO commits explicitly flagged
as open. This is pure mesh-loading coverage (no GL context needed -
GLMeshBuffer construction is the one part of this pipeline that
genuinely needs a real GPU context, load_link_set() itself does not),
matching this file family's own headless standard: real assertions
against real return values, no mocked file I/O.
"""
import sys
from pathlib import Path

sys.path.insert(0, ".")
from hydra_suite.render.mesh import load_link_set
from hydra_suite.render.pnp_rig import (
    PNP_ALL_MESH_FILES,
    PNP_ALL_MESH_NAMES,
    PNP_BASE_STATIC_PARTS,
    PNP_LINK_NAMES,
    PNP_MESH_DIR,
    PNP_STATIC_PART_OWNER,
    PNP_X_CARRIAGE_STATIC_PARTS,
    PNP_Y_CARRIAGE_STATIC_PARTS,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "meshes"


def main() -> None:
    # --- real part-list shape: no dupes, every part has exactly one owner ---
    all_static_parts = PNP_BASE_STATIC_PARTS + PNP_Y_CARRIAGE_STATIC_PARTS + PNP_X_CARRIAGE_STATIC_PARTS
    assert len(all_static_parts) == 160, f"expected 160 real static parts, got {len(all_static_parts)}"
    assert len(all_static_parts) == len(set(all_static_parts)), "a static part name is listed under more than one owner"
    assert set(PNP_STATIC_PART_OWNER) == set(all_static_parts)
    for name in PNP_STATIC_PART_OWNER.values():
        assert name in ("base", "y_carriage", "x_carriage"), f"unknown real owner link: {name!r}"

    assert len(PNP_ALL_MESH_NAMES) == 167, f"expected 7 kinematic + 160 static = 167, got {len(PNP_ALL_MESH_NAMES)}"
    assert set(PNP_ALL_MESH_NAMES) == set(PNP_LINK_NAMES) | set(all_static_parts)
    assert set(PNP_ALL_MESH_FILES) == set(PNP_ALL_MESH_NAMES)

    # --- every real .stl this maps to genuinely exists and parses, with
    # real geometry - not just that the Python-side bookkeeping is
    # internally consistent. ---
    meshes = load_link_set(ASSETS_DIR / PNP_MESH_DIR, PNP_ALL_MESH_FILES)
    assert len(meshes) == 167
    for name in PNP_ALL_MESH_NAMES:
        mesh = meshes[name]
        assert mesh.vertices.shape[0] > 0, f"{name} loaded with zero vertices"
        assert mesh.vertices.shape == mesh.normals.shape, f"{name} vertex/normal count mismatch"

    print(
        f"VERIFY_PNP_STATIC_PARTS=PASS kinematic_links={len(PNP_LINK_NAMES)} "
        f"static_parts={len(all_static_parts)} total_meshes_loaded={len(meshes)}"
    )


if __name__ == "__main__":
    main()
