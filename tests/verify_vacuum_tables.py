# =============================================================================
# HYDRA-UMC-SUITE - tests/verify_vacuum_tables.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The vacuum-table module went from a bare parametric box to a catalog of
# six real STL models shared byte-for-byte with HYDRA-UMC-STUDIO's own
# public/models/vacuum-tables/. This verifies the parts NOT already covered
# by verify_module_config_panel.py's panel-level checks: that every catalog
# STL is a valid binary mesh whose real bounding box matches its declared
# millimetre dimensions once module_rig places it in the Y-up metre world,
# and that select_vacuum_table()/vacuum_table_model() honour the same
# whitelist-and-preserve contract STUDIO's src/vacuumTables.ts does.
#
# Named verify_* (not test_*) on purpose - tools/run_offline_verifiers.py
# only discovers verify_*.py, matching this repo's own convention (see that
# runner's own header). No Qt, no network.
# =============================================================================
import struct
import sys

sys.path.insert(0, ".")

import numpy as np

from hydra_suite.vacuum_tables import (
    CATALOG_DIR,
    VACUUM_TABLE_MODELS,
    select_vacuum_table,
    vacuum_table_model,
)
from hydra_suite.render.module_rig import module_segment_mesh, module_segments

failures = 0


def check(label, ok):
    global failures
    if ok:
        print(f"ok   {label}")
    else:
        print(f"FAIL {label}")
        failures += 1


def run():
    check("catalog exposes exactly six unique model ids", len({m["id"] for m in VACUUM_TABLE_MODELS}) == 6)

    for model in VACUUM_TABLE_MODELS:
        mid = model["id"]
        data = (CATALOG_DIR / model["file"]).read_bytes()
        triangles = struct.unpack_from("<I", data, 80)[0]
        check(f"{mid}: STL declares a positive triangle count", triangles > 0)
        check(f"{mid}: STL byte length matches its triangle count", len(data) == 84 + triangles * 50)

        segment = module_segments("vacuumTable", model["width"], model["length"], mid)[0]
        mesh = module_segment_mesh(segment)
        check(f"{mid}: mesh vertices are all finite", bool(np.isfinite(mesh.vertices).all()))
        check(f"{mid}: mesh normals are all finite", bool(np.isfinite(mesh.normals).all()))

        # Y-up world in metres: X = width, Y = totalHeight, Z = length.
        span = np.ptp(mesh.vertices, axis=0)
        expected = np.array([model["width"] / 1000, model["totalHeight"] / 1000, model["length"] / 1000])
        check(f"{mid}: world bounding box matches catalog dimensions", bool(np.allclose(span, expected, atol=1e-6)))
        centre_xz = (mesh.vertices.min(0) + mesh.vertices.max(0))[[0, 2]]
        check(f"{mid}: mesh is centred on X and Z", bool(np.allclose(centre_xz, [0, 0], atol=1e-6)))
        check(f"{mid}: mesh is grounded at Y=0", abs(float(mesh.vertices[:, 1].min())) < 1e-6)

    # Anisotropic resizing preserves grounding, thickness and cached originals.
    model = VACUUM_TABLE_MODELS[0]
    resized = module_segment_mesh(module_segments("vacuumTable", 80, 300, model["id"])[0])
    check("custom footprint and unchanged thickness", bool(np.allclose(np.ptp(resized.vertices, axis=0), [0.08, model["totalHeight"]/1000, 0.3])))
    check("custom normals remain finite", bool(np.isfinite(resized.normals).all()))
    original = module_segment_mesh(module_segments("vacuumTable", 160, 120, model["id"])[0])
    check("custom mesh never mutates cached original", bool(np.allclose(np.ptp(original.vertices, axis=0)[[0,2]], [0.16, 0.12])))
    from hydra_suite.vacuum_tables import resize_vacuum_table, vacuum_table_size
    legacy = {"modelId": model["id"], "size": {"width": 999, "length": 999}, "pumpActive": True}
    custom = resize_vacuum_table(legacy, "width", 165)
    check("legacy ignored, custom axis preserves other catalog dimension", vacuum_table_size(custom) == {"width": 165, "length": 120})
    check("pump preserved", custom["pumpActive"])
    for bad in (True, float('nan'), float('inf'), 0, 5001, 12.5):
        check(f"reject invalid custom dimension {bad}", resize_vacuum_table(custom, "length", bad) == custom)

    # --- select_vacuum_table(): whitelist ids, preserve everything else ---
    source = {
        "enabled": True,
        "pumpActive": True,
        "valveActive": True,
        "worldPos": {"x": 45, "y": 67},
        "worldRot": 1.5,
        "renderScale": 1,
        "size": {"width": 100, "length": 100},
        "extension": {"keep": True},
    }
    for model in VACUUM_TABLE_MODELS:
        selected = select_vacuum_table(source, model["id"])
        check(f"select {model['id']}: modelId written", selected["modelId"] == model["id"])
        check(
            f"select {model['id']}: size follows the catalog",
            selected["size"] == {"width": model["width"], "length": model["length"]},
        )
        preserved = all(
            selected[f] == source[f]
            for f in ("enabled", "pumpActive", "valveActive", "worldPos", "worldRot", "renderScale", "extension")
        )
        check(f"select {model['id']}: pump/valve/pose/extension preserved", preserved)

    check("select never mutates the source module in place", source["size"]["width"] == 100)
    check("select rejects a path-traversal id without touching state", select_vacuum_table(source, "../../bad.stl") == source)
    check("vacuum_table_model(None) falls back to the first model", vacuum_table_model(None)["id"] == "160x120x15")
    check("vacuum_table_model('unknown') falls back to the first model", vacuum_table_model("unknown")["id"] == "160x120x15")


run()

print()
if failures:
    print(f"FAILED: {failures} mismatches")
    sys.exit(1)
print("ALL VERIFY_VACUUM_TABLES CHECKS PASSED")
