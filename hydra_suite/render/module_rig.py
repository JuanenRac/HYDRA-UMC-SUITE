# =============================================================================
# HYDRA-UMC SUITE - render/module_rig.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Static module meshes for heated beds, vacuum tables and racks.
# CNC/Laser now use independent STL assemblies through pnp_rig.py and
# viewport.py, not the former primitive frame approximation.
#
# No joint chain here (these modules don't move) - every Segment's own
# `pos`/`rpy` is already a WORLD-space transform, unlike generic_rig.py's
# own per-joint-frame segments.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from hydra_suite.vacuum_tables import CATALOG_DIR, vacuum_table_model
from hydra_suite.heated_beds import CATALOG_DIR as HEATED_DIR, heated_bed_model
from hydra_suite.racks import ASSET_DIR as RACK_DIR, rack_geometry, rack_parts
from hydra_suite.render.mesh import Mesh, load_stl, make_box_mesh, make_cylinder_mesh

import numpy as np

from hydra_suite.render.kinematics import rot_x, rot_y, rot_z, translation

# Hex colors copied verbatim from SharedModule3DView.tsx.
_C_111827 = (0x11 / 255, 0x18 / 255, 0x27 / 255)
_C_1E293B = (0x1E / 255, 0x29 / 255, 0x3B / 255)
_C_0F172A = (0x0F / 255, 0x17 / 255, 0x2A / 255)
_C_334155 = (0x33 / 255, 0x41 / 255, 0x55 / 255)
_C_94A3B8 = (0x94 / 255, 0xA3 / 255, 0xB8 / 255)
_C_CBD5E1 = (0xCB / 255, 0xD5 / 255, 0xE1 / 255)
_C_EF4444 = (0xEF / 255, 0x44 / 255, 0x44 / 255)
_C_FCA5A5 = (0xFC / 255, 0xA5 / 255, 0xA5 / 255)  # laser beam - STUDIO renders this semi-transparent; this app's own shader has no alpha blending yet, so it draws opaque (a real, honest simplification, not a redesign)
_C_B91C1C = (0xB9 / 255, 0x1C / 255, 0x1C / 255)
_C_0A0F14 = (0x0A / 255, 0x0F / 255, 0x14 / 255)

MODULE_TYPES: tuple[str, ...] = ("heatedBed", "vacuumTable")


@dataclass(frozen=True)
class Segment:
    kind: str  # "cylinder", "box", "vacuum_stl" or "heated_stl"
    size: tuple[float, float, float]  # cylinder: (radius_top, radius_bottom, height) ; box: (width, height, depth)
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)
    color: tuple[float, float, float] = _C_1E293B
    model_id: str | None = None


def segment_world_transform(seg: Segment) -> np.ndarray:
    return translation(seg.pos) @ rot_x(seg.rpy[0]) @ rot_y(seg.rpy[1]) @ rot_z(seg.rpy[2])


@lru_cache(maxsize=6)
def _vacuum_table_mesh(model_id: str) -> Mesh:
    model = vacuum_table_model(model_id)
    mesh = load_stl(CATALOG_DIR / model["file"])
    # STL is authored in mm; load_stl converts to meters. Center XY, rotate
    # CAD Z-up to world Y-up. Match STUDIO exactly; never scale to legacy size.
    vertices = mesh.vertices.copy()
    vertices[:, 0] -= model["width"] / 2000.0
    vertices[:, 1] -= model["length"] / 2000.0
    rotation = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float32)
    return Mesh(vertices @ rotation.T, mesh.normals @ rotation.T)


@lru_cache(maxsize=4)
def _heated_bed_mesh(model_id: str) -> Mesh:
    model = heated_bed_model(model_id)
    mesh = load_stl(HEATED_DIR / model["file"])
    vertices = mesh.vertices.copy()
    vertices[:, 0] -= model["width"] / 2000.0
    vertices[:, 1] -= model["length"] / 2000.0
    rotation = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float32)
    return Mesh(vertices @ rotation.T, mesh.normals @ rotation.T)


def module_segment_mesh(segment: Segment) -> Mesh:
    if segment.kind == "rack_stl":
        source = _rack_mesh(segment.model_id)
        reference = {"base": (0.18, 0.02, 0.18), "wall": (0.01, 0.01, 0.16), "guide": (0.004, 0.003, 0.16)}
        scale = np.array(segment.size) / reference[segment.model_id]
        normals = source.normals / scale
        normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
        return Mesh(source.vertices * scale, normals)
    if segment.kind in ("vacuum_stl", "heated_stl"):
        heated = segment.kind == "heated_stl"
        model = heated_bed_model(segment.model_id) if heated else vacuum_table_model(segment.model_id)
        source = _heated_bed_mesh(model["id"]) if heated else _vacuum_table_mesh(model["id"])
        scale = np.array([segment.size[0] / (model["width"] / 1000), 1,
                          segment.size[2] / (model["length"] / 1000)], dtype=np.float32)
        # Transform a copy, never the cached source; inverse scale for normals.
        normals = source.normals / scale
        normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
        return Mesh(source.vertices * scale, normals)
    if segment.kind == "cylinder":
        return make_cylinder_mesh(*segment.size)
    return make_box_mesh(*segment.size)


@lru_cache(maxsize=3)
def _rack_mesh(part):
    if part not in ("base", "wall", "guide"):
        raise ValueError("Unknown rack STL component")
    mesh = load_stl(RACK_DIR / (part + ".stl"))
    vertices = mesh.vertices - (mesh.vertices.min(axis=0) + mesh.vertices.max(axis=0)) / 2
    rotation = np.array([[1,0,0], [0,0,1], [0,-1,0]], dtype=np.float32)
    return Mesh(vertices @ rotation.T, mesh.normals @ rotation.T)


def rack_segments(rack):
    if rack.get("type") == "None":
        return []
    spec = rack_geometry(rack)
    color = tuple(int(spec["color"][i:i+2], 16)/255 for i in (1,3,5))
    segs = [Segment("rack_stl", tuple(v/1000 for v in size),
                    pos=tuple(v/1000 for v in pos), color=color, model_id=part)
            for part, size, pos in rack_parts(rack)]
    # Opaque slot indicators in SUITE; STUDIO uses translucent indicators.
    slots = rack.get("usableSlots", [])
    for i in range(spec["capacity"]):
        valid = bool(slots[i]) if i < len(slots) else False
        segs.append(Segment("box", (spec["width"]/1000, .002, spec["depth"]/1000),
                            pos=(0, .04+i*.01, 0), color=color if valid else (1,0,0)))
    return segs


def module_segments(module_type: str, width_mm: float, length_mm: float, model_id: str | None = None) -> list[Segment]:
    """Real, world-space segment list for one of the supported static module
    types, matching STUDIO's mm-to-meter convention. Vacuum tables use
    their modelId geometry scaled to the footprint resolved by the caller.
    Other module types are handled by their dedicated renderers, not here."""
    w = max(0.001, width_mm / 1000.0)
    length = max(0.001, length_mm / 1000.0)
    if module_type == "vacuumTable":
        return [Segment("vacuum_stl", (w, 0, length), color=_C_94A3B8, model_id=vacuum_table_model(model_id)["id"])]
    if module_type == "heatedBed":
        return [Segment("heated_stl", (w, 0, length), color=(0.72, 0.45, 0.27), model_id=heated_bed_model(model_id)["id"])]
    return []
