# =============================================================================
# HYDRA-UMC SUITE - render/mesh.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# STL loading (via numpy-stl) - flat per-face normals, not smoothed/shared
# vertex normals. STL itself has no shared-vertex topology (every
# triangle repeats its own 3 corner points independently), so flat
# shading is the honest choice here rather than a vertex-averaging pass
# that would imply smoothness the source mesh doesn't actually encode.
# Same mm-vs-m scale detection every *Arm.tsx in HYDRA-UMC-STUDIO already
# applies to the same STL files, ported here rather than re-derived, since
# it's the same files and the same authoring-convention gap.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from stl import mesh as stl_mesh


@dataclass
class Mesh:
    """Flat vertex+normal arrays ready for a GL_TRIANGLES VBO - 3 vertices
    per triangle, no index buffer (matches STL's own non-indexed
    triangle-soup structure, no benefit to de-duplicating for meshes this
    small - largest of the 7 UR5e links is a few thousand triangles)."""

    vertices: np.ndarray  # (N, 3) float32
    normals: np.ndarray   # (N, 3) float32, one per vertex (== per-face, repeated 3x)

    @property
    def triangle_count(self) -> int:
        return len(self.vertices) // 3


def load_stl(path: str | Path) -> Mesh:
    raw = stl_mesh.Mesh.from_file(str(path))
    vertices = raw.vectors.reshape(-1, 3).astype(np.float32)

    # Same defensive mm-vs-m check HYDRA-UMC-STUDIO's own useRealScaleSTL()
    # applies (see e.g. src/components/3d/URArm.tsx) - these particular
    # UR5e STLs are already meter-scale in practice, but this costs
    # nothing to keep and guards the exact class of authoring-convention
    # bug that check exists for in the first place.
    span = vertices.max(axis=0) - vertices.min(axis=0)
    if float(np.max(span)) > 5.0:
        vertices = vertices * 0.001

    # One normal per triangle, repeated for its 3 vertices - raw.normals
    # is already per-face from numpy-stl's own cross-product computation.
    normals = np.repeat(raw.normals.astype(np.float32), 3, axis=0)
    # Guard against a degenerate (zero-length) normal on a bad/duplicate
    # triangle - normalizing a zero vector produces NaN, which would
    # blank out lighting for that triangle silently; clamp the divisor
    # instead of trusting every STL triangle is well-formed.
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths < 1e-12] = 1.0
    normals = normals / lengths

    return Mesh(vertices=vertices, normals=normals)


def load_link_set(directory: str | Path, link_files: dict[str, str]) -> dict[str, Mesh]:
    """Loads every named link's own STL from one folder - link_files maps
    a link name (see kinematics.py's own UR5E_LINK_NAMES) to its filename
    within `directory`, so the caller controls naming instead of this
    function guessing a convention."""
    directory = Path(directory)
    return {name: load_stl(directory / filename) for name, filename in link_files.items()}
