# =============================================================================
# HYDRA-UMC-SUITE - tests/mesh_unit_checks.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The unit of a mesh: declared by the model in its metadata.json, guessed from the size only when
# it is not. Also that every model folder of the shipped meshes declares its unit and that the
# declaration agrees with what the size check would have decided. No Qt, no network.
# Run by verify_machine_assets.py.
# =============================================================================
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from stl import mesh as stl_mesh

from hydra_suite.render.mesh import declared_unit, load_stl, normalize_unit


def _write_cube(path: Path, side: float) -> None:
    cube = stl_mesh.Mesh(np.zeros(2, dtype=stl_mesh.Mesh.dtype))
    cube.vectors[0] = [[0, 0, 0], [side, 0, 0], [0, side, side]]
    cube.vectors[1] = [[side, 0, 0], [side, side, side], [0, side, side]]
    cube.save(str(path))


def _span(mesh) -> float:
    return float(np.max(mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)))


def run_mesh_unit_checks(meshes_root: Path) -> int:
    """Number of checks run; raises AssertionError with the label of the first one that fails."""
    count = 0

    def check(label: str, ok: bool) -> None:
        nonlocal count
        assert ok, label
        count += 1

    check("unit names are normalised", normalize_unit(" MM ") == "mm" and normalize_unit("Meters") == "m")
    check("an unknown unit is not a unit", normalize_unit("cm") is None and normalize_unit(3) is None)

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "model" / "links"
        folder.mkdir(parents=True)
        big = folder / "a.stl"
        small = folder / "b.stl"
        _write_cube(big, 100.0)
        _write_cube(small, 0.4)
        metadata = Path(tmp) / "model" / "metadata.json"
        check("no metadata declares nothing", declared_unit(big) is None)
        check("undeclared 100 is taken for millimeters", abs(_span(load_stl(big)) - 0.1) < 1e-6)
        check("undeclared 0.4 stays in meters", abs(_span(load_stl(small)) - 0.4) < 1e-6)
        metadata.write_text(json.dumps({"unit": "m"}), encoding="utf-8")
        check("the metadata of a folder above is found", declared_unit(big) == "m")
        check("a declared meter is never scaled, however big", abs(_span(load_stl(big)) - 100.0) < 1e-3)
        metadata.write_text(json.dumps({"unit": "mm"}), encoding="utf-8")
        check("a declared millimeter is scaled, however small", abs(_span(load_stl(small)) - 0.0004) < 1e-7)
        check("an explicit unit beats the metadata", abs(_span(load_stl(small, unit="m")) - 0.4) < 1e-6)
        metadata.write_text("{not json", encoding="utf-8")
        check("a broken metadata file falls back to the size", declared_unit(big) is None)

    models = sorted(p.parent for p in meshes_root.rglob("metadata.json"))
    check("there are shipped models", len(models) > 0)
    for folder in models:
        stls = sorted(folder.rglob("*.stl"))
        if not stls:
            continue
        unit = declared_unit(stls[0])
        check(f"{folder.name} declares its unit", unit is not None)
        for stl in stls:
            raw = stl_mesh.Mesh.from_file(str(stl)).vectors.reshape(-1, 3)
            guessed = "mm" if float(np.max(raw.max(axis=0) - raw.min(axis=0))) > 5.0 else "m"
            check(f"{folder.name}/{stl.name}: the declared unit agrees with the size", guessed == unit)
    return count
