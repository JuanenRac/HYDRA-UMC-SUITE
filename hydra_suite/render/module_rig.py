# =============================================================================
# HYDRA-UMC SUITE - render/module_rig.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Live 3D preview geometry for the 4 tool-attachment modules that get one
# in HYDRA-UMC-STUDIO's own source (CNC/Laser/Heated Bed/Vacuum Table via
# src/components/3d/SharedModule3DView.tsx). Vacuum tables load real STL;
# the other modules retain their matching primitive geometry (same shapes,
# same positions, same hex colors, same real world/mm-to-meter scale)
# rather than invented fresh, so this app's own module preview looks
# like the one the web UI shows for the same module.
#
# STUDIO's own SharedModule3DView.tsx additionally covers juanenPnP/
# lumenPnP via a real GLB-mesh rig (LumenPnPRig.tsx) - a genuinely
# separate, larger piece of work (real mesh loading, not primitives),
# tracked separately, not part of this file.
#
# No joint chain here (these modules don't move) - every Segment's own
# `pos`/`rpy` is already a WORLD-space transform, unlike generic_rig.py's
# own per-joint-frame segments.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from hydra_suite.vacuum_tables import CATALOG_DIR, vacuum_table_model
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

MODULE_TYPES: tuple[str, ...] = ("juanenCNC", "juanenLaser", "heatedBed", "vacuumTable")


@dataclass(frozen=True)
class Segment:
    kind: str  # "cylinder", "box" or "vacuum_stl"
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


def module_segment_mesh(segment: Segment) -> Mesh:
    if segment.kind == "vacuum_stl":
        return _vacuum_table_mesh(vacuum_table_model(segment.model_id)["id"])
    if segment.kind == "cylinder":
        return make_cylinder_mesh(*segment.size)
    return make_box_mesh(*segment.size)


def _heated_bed_segments(w: float, length: float) -> list[Segment]:
    return [
        Segment("box", (w, 0.02, length), pos=(0, 0.01, 0), color=_C_B91C1C),
        Segment("box", (max(0.01, w - 0.02), 0.005, max(0.01, length - 0.02)), pos=(0, 0.0225, 0), color=_C_EF4444),
    ]


def _lumen_style_frame_segments(w: float, length: float, is_cnc: bool) -> list[Segment]:
    """Ported from SharedModule3DView.tsx's own LumenStyleFrame() - the
    isPnp-only bits (feeders, camera ring, dual-nozzle toolhead) are
    real there too but never reached for juanenCNC/juanenLaser (isPnp is
    always false for those 2 module keys), so they're not ported here."""
    segs = [
        # Legs
        Segment("box", (0.02, 0.1, 0.04), pos=(-w / 2 + 0.01, 0.05, -length / 2 + 0.02), color=_C_111827),
        Segment("box", (0.02, 0.1, 0.04), pos=(w / 2 - 0.01, 0.05, -length / 2 + 0.02), color=_C_111827),
        Segment("box", (0.02, 0.1, 0.04), pos=(-w / 2 + 0.01, 0.05, length / 2 - 0.02), color=_C_111827),
        Segment("box", (0.02, 0.1, 0.04), pos=(w / 2 - 0.01, 0.05, length / 2 - 0.02), color=_C_111827),
        # Y Rails
        Segment("box", (0.03, 0.03, length), pos=(-w / 2 + 0.015, 0.115, 0), color=_C_1E293B),
        Segment("box", (0.03, 0.03, length), pos=(w / 2 - 0.015, 0.115, 0), color=_C_1E293B),
        # Base frame crossbars
        Segment("box", (w - 0.04, 0.02, 0.02), pos=(0, 0.04, -length / 2 + 0.01), color=_C_1E293B),
        Segment("box", (w - 0.04, 0.02, 0.02), pos=(0, 0.04, length / 2 - 0.01), color=_C_1E293B),
        # Bed
        Segment("box", (w - 0.06, 0.005, length - 0.1), pos=(0, 0.06, 0), color=_C_0F172A),
        # X Gantry
        Segment("box", (w, 0.03, 0.03), pos=(0, 0.14, 0), color=_C_1E293B),
        # Y Motor
        Segment("box", (0.04, 0.04, 0.05), pos=(-w / 2 - 0.01, 0.12, -length / 2 + 0.02), color=_C_334155),
        # Toolhead body (group at 0, 0.14, 0.025 in STUDIO's own nested-group source, flattened here)
        Segment("box", (0.05, 0.06, 0.04), pos=(0, 0.14, 0.025), color=_C_1E293B),
    ]
    if is_cnc:
        segs += [
            Segment("box", (0.03, 0.04, 0.02), pos=(0, 0.13, 0.045), color=_C_334155),
            Segment("cylinder", (0.01, 0.01, 0.03), pos=(0, 0.11, 0.045), color=_C_94A3B8),
            Segment("cylinder", (0.002, 0.001, 0.02), pos=(0, 0.09, 0.045), color=_C_CBD5E1),
        ]
    else:  # laser
        segs += [
            Segment("box", (0.03, 0.04, 0.02), pos=(0, 0.13, 0.045), color=_C_334155),
            Segment("cylinder", (0.01, 0.01, 0.03), pos=(0, 0.11, 0.045), color=_C_EF4444),
            Segment("cylinder", (0.001, 0.001, 0.05), pos=(0, 0.08, 0.045), color=_C_FCA5A5),
        ]
    return segs


def module_segments(module_type: str, width_mm: float, length_mm: float, model_id: str | None = None) -> list[Segment]:
    """Real, world-space segment list for one of the 4 supported module
    types, matching STUDIO's mm-to-meter convention. Vacuum tables use
    their fixed modelId geometry and ignore legacy width/length values.
    Other module types are handled by their dedicated renderers, not here."""
    w = max(0.001, width_mm / 1000.0)
    length = max(0.001, length_mm / 1000.0)
    if module_type == "vacuumTable":
        return [Segment("vacuum_stl", (0, 0, 0), color=_C_94A3B8, model_id=vacuum_table_model(model_id)["id"])]
    if module_type == "heatedBed":
        return _heated_bed_segments(w, length)
    if module_type == "juanenCNC":
        return _lumen_style_frame_segments(w, length, is_cnc=True)
    if module_type == "juanenLaser":
        return _lumen_style_frame_segments(w, length, is_cnc=False)
    return []
