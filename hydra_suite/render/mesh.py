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

import json
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


# The unit of the meshes of a model is declared in the `metadata.json` of its folder (`"unit": "mm"` or
# `"m"`). Only a model that does not declare it falls back to the size check below.
MILLIMETER_SPAN = 5.0  # a link longer than this many meters in any axis is taken for a millimeter mesh
_UNIT_NAMES = {
    "mm": "mm", "millimeter": "mm", "millimeters": "mm", "millimetre": "mm", "millimetres": "mm",
    "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
}
_METADATA_LEVELS = 4


def normalize_unit(value: object) -> str | None:
    """"mm" or "m" for a declared unit, None for anything else."""
    if not isinstance(value, str):
        return None
    return _UNIT_NAMES.get(value.strip().lower())


def declared_unit(path: str | Path) -> str | None:
    """The unit the `metadata.json` next to a mesh, or in the folders above it, declares for the model."""
    folder = Path(path).resolve().parent
    for _ in range(_METADATA_LEVELS):
        metadata = folder / "metadata.json"
        if metadata.is_file():
            try:
                data = json.loads(metadata.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            return normalize_unit(data.get("unit", data.get("units"))) if isinstance(data, dict) else None
        if folder.parent == folder:
            break
        folder = folder.parent
    return None


def to_meters(vertices: np.ndarray, unit: str | None) -> np.ndarray:
    """Brings the vertices to meters. A declared unit decides; without one, a mesh bigger than
    MILLIMETER_SPAN in any axis is taken for millimeters (the check STUDIO's useRealScaleSTL() applies)."""
    if unit == "mm":
        return vertices * 0.001
    if unit == "m":
        return vertices
    span = vertices.max(axis=0) - vertices.min(axis=0)
    return vertices * 0.001 if float(np.max(span)) > MILLIMETER_SPAN else vertices


def load_stl(path: str | Path, unit: str | None = None) -> Mesh:
    raw = stl_mesh.Mesh.from_file(str(path))
    vertices = to_meters(raw.vectors.reshape(-1, 3).astype(np.float32), unit or declared_unit(path))
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


def make_cylinder_mesh(radius_top: float, radius_bottom: float, height: float, segments: int = 20) -> Mesh:
    """A Y-axis cylinder (optionally tapered into a frustum, matching
    three.js CylinderGeometry(radiusTop, radiusBottom, height)'s own
    convention) centered on its own local origin, spanning
    [-height/2, +height/2] - generated directly at its real size (not a
    unit primitive plus a non-uniform scale matrix), since a tapered
    cylinder's side-wall slope can't be produced by scaling a cylindrical
    primitive uniformly in X/Z. Used for HYDRA-UMC SUITE's own "Generic"
    robot rig (render/generic_rig.py) - the same primitive-built fallback
    HYDRA-UMC-STUDIO's own GenericRobotArm.tsx uses via drei's <Cylinder>,
    ported to raw geometry here since this app has no such helper library."""
    half_h = height / 2.0
    verts: list[tuple[float, float, float]] = []
    norms: list[tuple[float, float, float]] = []

    angles = [2 * np.pi * i / segments for i in range(segments + 1)]
    slope = (radius_bottom - radius_top) / height if height > 1e-9 else 0.0

    # Side wall - one quad (2 triangles) per segment, sloped normals for a tapered wall.
    for i in range(segments):
        a0, a1 = angles[i], angles[i + 1]
        x0t, z0t = radius_top * np.cos(a0), radius_top * np.sin(a0)
        x1t, z1t = radius_top * np.cos(a1), radius_top * np.sin(a1)
        x0b, z0b = radius_bottom * np.cos(a0), radius_bottom * np.sin(a0)
        x1b, z1b = radius_bottom * np.cos(a1), radius_bottom * np.sin(a1)
        n0 = np.array([np.cos(a0), slope, np.sin(a0)])
        n0 = n0 / np.linalg.norm(n0)
        n1 = np.array([np.cos(a1), slope, np.sin(a1)])
        n1 = n1 / np.linalg.norm(n1)
        top0, top1 = (x0t, half_h, z0t), (x1t, half_h, z1t)
        bot0, bot1 = (x0b, -half_h, z0b), (x1b, -half_h, z1b)
        for v, n in ((top0, n0), (bot0, n0), (bot1, n1)):
            verts.append(v)
            norms.append(tuple(n))
        for v, n in ((top0, n0), (bot1, n1), (top1, n1)):
            verts.append(v)
            norms.append(tuple(n))

    # Caps - simple triangle fans, flat normal straight up/down.
    if radius_top > 1e-9:
        center = (0.0, half_h, 0.0)
        for i in range(segments):
            a0, a1 = angles[i], angles[i + 1]
            p0 = (radius_top * np.cos(a0), half_h, radius_top * np.sin(a0))
            p1 = (radius_top * np.cos(a1), half_h, radius_top * np.sin(a1))
            for v in (center, p1, p0):
                verts.append(v)
                norms.append((0.0, 1.0, 0.0))
    if radius_bottom > 1e-9:
        center = (0.0, -half_h, 0.0)
        for i in range(segments):
            a0, a1 = angles[i], angles[i + 1]
            p0 = (radius_bottom * np.cos(a0), -half_h, radius_bottom * np.sin(a0))
            p1 = (radius_bottom * np.cos(a1), -half_h, radius_bottom * np.sin(a1))
            for v in (center, p0, p1):
                verts.append(v)
                norms.append((0.0, -1.0, 0.0))

    return Mesh(vertices=np.array(verts, dtype=np.float32), normals=np.array(norms, dtype=np.float32))


def make_box_mesh(width: float, height: float, depth: float) -> Mesh:
    """An axis-aligned box centered on its own local origin - stands in
    for drei's <RoundedBox> in the Generic rig (render/generic_rig.py):
    the rounding itself is a cosmetic bevel with no kinematic meaning, so
    a plain box is the honest simplification rather than pulling in a
    dedicated rounded-geometry generator for one fallback rig."""
    x, y, z = width / 2.0, height / 2.0, depth / 2.0
    faces = [
        # (normal, 4 corners in CCW winding as seen from outside)
        ((0, 0, 1), [(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]),
        ((0, 0, -1), [(x, -y, -z), (-x, -y, -z), (-x, y, -z), (x, y, -z)]),
        ((0, 1, 0), [(-x, y, z), (x, y, z), (x, y, -z), (-x, y, -z)]),
        ((0, -1, 0), [(-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z)]),
        ((1, 0, 0), [(x, -y, z), (x, -y, -z), (x, y, -z), (x, y, z)]),
        ((-1, 0, 0), [(-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z)]),
    ]
    verts: list[tuple[float, float, float]] = []
    norms: list[tuple[float, float, float]] = []
    for n, corners in faces:
        c0, c1, c2, c3 = corners
        for v in (c0, c1, c2):
            verts.append(v)
            norms.append(n)
        for v in (c0, c2, c3):
            verts.append(v)
            norms.append(n)
    return Mesh(vertices=np.array(verts, dtype=np.float32), normals=np.array(norms, dtype=np.float32))
