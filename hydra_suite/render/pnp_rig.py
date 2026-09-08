# =============================================================================
# HYDRA-UMC SUITE - render/pnp_rig.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real 3D kinematics for the LumenPnP/JuanenPnP tool-attachment modules
# (juanenPnP/lumenPnP), matching HYDRA-UMC-STUDIO's own real-mesh
# LumenPnPRig.tsx - unlike module_rig.py's 4 primitive-built modules
# (CNC/Laser/HeatedBed/VacuumTable), this one drives real STL meshes
# (assets/meshes/lumenpnp/, see that folder's own ATTRIBUTION.txt) posed
# through a real, if simple, Cartesian gantry chain - not a serial robot
# joint chain (see kinematics.py's own UR/quaternion families), and not a
# flat WORLD-space Segment list either (module_rig.py's modules are
# static; this one actually moves per axisX/axisY/axisZ/nozzle1Rotation/
# nozzle2Rotation, same fields ui/panels/pick_and_place_panel.py's own
# PNP_AXES sliders already write).
#
# STUDIO's own LumenPnPRig.tsx loads a pre-merged .glb (a browser-specific
# workaround, not a format requirement - see assets/meshes/lumenpnp/
# ATTRIBUTION.txt for why) but keeps the raw .stl files as source of
# truth; this app loads those .stl files directly via mesh.py's existing
# load_link_set(), the same real loading path every other robot mesh in
# this app already uses - no new mesh format support was needed.
#
# Real gantry hierarchy (ported 1:1 from LumenPnPRig.tsx's own nested
# <group> structure - world transform = parent transform composed with
# each child's own local step, same convention as kinematics.py's own
# ur_world_link_transforms()):
#   base (fixed)
#     -> y_carriage   (translates world Y,  0-487mm - openpnp/machine.xml)
#        -> x_carriage (translates local X, 0-433mm - openpnp/machine.xml)
#           -> z_carriage_left  (translates local Z only - the rail
#              slider housing, does NOT rotate on the real machine)
#              -> nozzle_left    (rotates about Z only - nozzle 1)
#           -> z_carriage_right (translates local Z only, same Z travel
#              as z_carriage_left)
#              -> nozzle_right   (rotates about Z only - nozzle 2)
#
# Real bug fixed 2026-09-08, ported from the same fix in LumenPnPRig.tsx:
# this used to merge each Z-carriage housing and its nozzle into ONE rigid
# transform (z_carriage_n1/n2) that translated AND rotated together - a
# real, visible error, since the housing's own real footprint at that
# joint is ~44x51mm (measured off the real per-part CAD bounding box), so
# the whole rectangular slider block would visibly swing around the Z axis
# every time a nozzle rotated, which the physical machine never does (only
# the ~10x10mm nozzle barrel itself spins). Splitting them into the 7
# links above - matching this project's own formal lumenpnp_juanenpnp.urdf
# link-for-link - fixes it: only nozzle_left/nozzle_right rotate now.
# =============================================================================
from __future__ import annotations

import numpy as np

from hydra_suite.render.kinematics import DEG, rot_x, rot_z, translation

# ROS/CAD is Z-up; this app's own world (matching Three.js/HYDRA-UMC-STUDIO,
# see kinematics.py's own header) is Y-up - the same single fixed root
# rotation LumenPnPRig.tsx's own outer <group rotation={[-Math.PI/2,0,0]}>
# applies, and the same convention kinematics.py's own UR_ROOT already
# uses for the same reason.
#
# GROUND_OFFSET_M ported from the same real fix in LumenPnPRig.tsx
# (2026-09-08): CAD Z=0 is the machine's own WORK surface (where
# openpnp's real 0-90mm Z-axis travel starts), not its feet - the real
# legs (once wired into this app's own PNP_MESH_FILES, still pending,
# see this repo's own CHANGELOG) reach down to Z=-100.81mm
# (front-leg-extension's own real bbox min - HYDRA-UMC-STUDIO's
# public/models/lumenpnp/parts/manifest.json). Composed here now, ahead
# of that wiring, so the offset is already correct the day it lands
# instead of reintroducing the same "half the machine hidden below the
# floor" bug found live on STUDIO.
GROUND_OFFSET_M = 0.10081
PNP_ROOT = translation((0.0, GROUND_OFFSET_M, 0.0)) @ rot_x(-np.pi / 2)

PNP_MESH_DIR = "lumenpnp"
PNP_LINK_NAMES: tuple[str, ...] = (
    "base", "y_carriage", "x_carriage",
    "z_carriage_left", "z_carriage_right",
    "nozzle_left", "nozzle_right",
)
PNP_MESH_FILES: dict[str, str] = {name: f"{name}.stl" for name in PNP_LINK_NAMES}

# 160 real, individually-named CAD parts (assets/meshes/lumenpnp/parts/ -
# legs, control box, frame extrusions, cameras/lights, feeders, motors,
# pulleys, belts, the real drag chains, and more) mirroring HYDRA-UMC-
# STUDIO's own LumenPnPRig.tsx batches 1-5 (2026-09-08) - wired in here
# now for real, closing the "SUITE has the data but pnp_rig.py never
# loads it" gap those STUDIO commits explicitly flagged as open. Each
# part is already in real assembled world-space (no per-part offset
# needed) and is attached to whichever of base/y_carriage/x_carriage
# matches its own real mechanical role - see
# assets/meshes/lumenpnp/ATTRIBUTION.txt and parts/manifest.json for the
# full per-part reasoning (STUDIO's own commit messages document it
# batch by batch; not re-derived independently here).
PNP_BASE_STATIC_PARTS: tuple[str, ...] = (
    'back-leg', 'back-leg001', 'back-leg-extension_001', 'back-leg-extension_002', 'front-left-leg',
    'front-right-leg', 'front-leg-extension_001', 'front-leg-extension_002', 'control-box_001', 'control-box-lid',
    'vslot-extrusion-20mmx20mmx600mm', 'vslot-extrusion-20mmx20mmx600mm001', 'vslot-extrusion-20mmx20mmx600mm002',
    'vslot-extrusion-20mmx20mmx600mm003', 'vslot-extrusion-20mmx20mmx600mm007',
    'vslot-extrusion-20mmx20mmx600mm008', 'vslot-extrusion-20mmx20mmx600mm009', 'bottom-camera-cover',
    'bottom-camera-mount', 'bottom-camera_001', 'top-camera001', 'bottom-light-mount', 'top-light-mount',
    'bottom-ring-light', 'top-ring-light', 'aux-staging-plate-foot', '8mm-strip-feeder', '12mm-strip-feeder',
    '16mm-strip-feeder', '24mm-strip-feeder', '32mm-strip-feeder', 'adj-strip-feeder', 'vacuum-pump002',
    'solenoid-valve003', 'nozzle-rack', 'nozzle-holder_001', 'nozzle-holder_002', 'xy-limit_001',
    'NEMA17-stepper003', 'NEMA17-stepper004', 'GT2-pulley002', 'GT2-pulley003', 'GT2-idler002', 'GT2-idler003',
    'y-gantry-gt2-belt_left', 'y-gantry-gt2-belt_right', 'y1-belt-tension-arm', 'y2-belt-tension-arm',
    'datum-board', 'datum-board-mount', 'secondary-fid-mount_001', 'blade12_004', 'blade13_003',
    'pcb-staging-plate', 'pcb-staging-plate-aux', 'peek-cable-clamp', 'peek-cable-clamp004', 'peek-cable-2',
    '550mm-MGN12H001_001', '550mm-MGN12H001_002', 'extrusion-cable-clip', 'extrusion-cable-clip002',
    'extrusion-cable-clip003', 'blade12_005', 'blade13_004', 'vacuum-pump003', 'solenoid-valve004', 'n40-nozzle',
    'n08-nozzle', 'reducing-union-tee-4-6-4', 'reducing-union-tee-4-6-4_01', 'corner-bracket006',
    'corner-bracket007', 'board-mount-static_001', 'board-mount-dynamic_001', 'board-support_001',
    'extrusion-cable-clip004', 'extrusion-cable-clip005',
)

# Fixed to the Y-bridge's own ends (moves with y_carriage in Y, not with
# x_carriage in X) - same real precedent as X-Motor above (a fixed-to-
# the-bridge part, not carried by the toolhead). Includes the real Y
# drag chain (30 links + 4 end connectors), rendered as one rigid
# attachment to the bridge - this rig has no cable-chain physics.
PNP_Y_CARRIAGE_STATIC_PARTS: tuple[str, ...] = (
    'x-idler-mount', 'x-motor-mount', 'y-gantry-left002', 'y-gantry-right002', 'y-limit-striker_Body_001',
    'squaring-bracket', 'NEMA17-stepper006', 'GT2-pulley005', 'GT2-idler005', 'y-drag-chain-link-001',
    'y-drag-chain-link-002', 'y-drag-chain-link-003', 'y-drag-chain-link-004', 'y-drag-chain-link-005',
    'y-drag-chain-link-006', 'y-drag-chain-link-007', 'y-drag-chain-link-008', 'y-drag-chain-link-009',
    'y-drag-chain-link-010', 'y-drag-chain-link-011', 'y-drag-chain-link-012', 'y-drag-chain-link-013',
    'y-drag-chain-link-014', 'y-drag-chain-link-015', 'y-drag-chain-link-016', 'y-drag-chain-link-017',
    'y-drag-chain-link-018', 'y-drag-chain-link-019', 'y-drag-chain-link-020', 'y-drag-chain-link-021',
    'y-drag-chain-link-022', 'y-drag-chain-link-023', 'y-drag-chain-link-024', 'y-drag-chain-link-025',
    'y-drag-chain-link-026', 'y-drag-chain-link-027', 'y-drag-chain-link-028', 'y-drag-chain-link-029',
    'y-drag-chain-link-030', 'ldo-drag-chain-end_Body_001', 'ldo-drag-chain-end_Body_003',
    'ldo-drag-chain-end_Body_005', 'ldo-drag-chain-end_Body_006', 'x-gantry-gt2-belt', 'x-belt-tension-arm',
    'belt-clamp009', 'belt-clamp010', 'belt-clamp013', 'belt-clamp014', 'x-cable-chain-support', '525mm-MGN12H',
    'MGN12H-linear-rail-carriage', 'MGN12H-linear-rail-carriage001', 'drag-chain-link_001', 'drag-chain-link_002',
    'drag-chain-link_003', 'drag-chain-link_004',
)

# The toolhead's own front/back gantry plates and everything else that
# rides with it in X (its own rotation motors, rails, belt/limit
# hardware).
PNP_X_CARRIAGE_STATIC_PARTS: tuple[str, ...] = (
    'nozzle-camera-mask_001', 'x-gantry-back', 'x-gantry-front', 'NEMA17-stepper005', 'GT2-pulley004',
    'GT2-idler004', 'z-belt-loop', 'belt-clamp007', 'belt-clamp008', 'mgn9-linear-rail-carriage',
    'mgn9-linear-rail-carriage001', 'linear-rail-100mm_001', 'linear-rail-100mm_002', 'z-gantry-backplate-left001',
    'z-gantry-backplate-right002', 'z-gantry-left001', 'z-gantry-right001', 'z-limit_001',
    'NEMA11-hollow-shaft-stepper002', 'NEMA11-hollow-shaft-stepper003', 'nozzle-camera-mask_002', 'MGN12H001_002',
    'cable-splay', 'rotary-pneumatic-adapter_001', 'rotary-pneumatic-adapter_002',
)

# Real link a static part attaches to, for every one of the 160 parts
# above - used both to load them under a common mesh-buffer namespace
# (PNP_STATIC_PART_FILES below) and to know which of the 7 real
# transforms pnp_world_link_transforms() returns applies to each one.
PNP_STATIC_PART_OWNER: dict[str, str] = {
    **{name: "base" for name in PNP_BASE_STATIC_PARTS},
    **{name: "y_carriage" for name in PNP_Y_CARRIAGE_STATIC_PARTS},
    **{name: "x_carriage" for name in PNP_X_CARRIAGE_STATIC_PARTS},
}
PNP_STATIC_PART_FILES: dict[str, str] = {name: f"parts/{name}.stl" for name in PNP_STATIC_PART_OWNER}

# What viewport.py's own _load_mesh_set() actually needs to load every
# real mesh (the 7 kinematic links + all 160 static parts) into ONE
# buffer set, keyed by name.
PNP_ALL_MESH_NAMES: tuple[str, ...] = PNP_LINK_NAMES + tuple(PNP_STATIC_PART_OWNER)
PNP_ALL_MESH_FILES: dict[str, str] = {**PNP_MESH_FILES, **PNP_STATIC_PART_FILES}

# Real fixed hardware travel bounds (openpnp/machine.xml) - same values
# ui/panels/pick_and_place_panel.py's own PNP_AXES sliders already clamp
# to; kept here too since a caller driving this module directly (rather
# than through that panel) should have the real bounds available without
# reaching into UI code for them.
PNP_AXIS_X_RANGE_MM = (0.0, 433.0)
PNP_AXIS_Y_RANGE_MM = (0.0, 487.0)
PNP_AXIS_Z_RANGE_MM = (0.0, 90.0)


def pnp_world_link_transforms(
    axis_x_mm: float,
    axis_y_mm: float,
    axis_z_mm: float,
    nozzle1_deg: float,
    nozzle2_deg: float,
) -> dict[str, np.ndarray]:
    """One 4x4 world transform per real link - base/y_carriage/x_carriage/
    z_carriage_left/z_carriage_right/nozzle_left/nozzle_right, matching
    PNP_LINK_NAMES exactly. Millimeter inputs (matching openpnp/machine.xml's
    own units and this module's own PNP_AXIS_*_RANGE_MM, same convention
    `module.get(field, 0)` already stores raw in RobotView's module() dict)
    are converted to meters here, at the one point they're consumed - same
    convention every other real-geometry helper in this folder uses."""
    x = axis_x_mm / 1000.0
    y = axis_y_mm / 1000.0
    z = axis_z_mm / 1000.0

    base_t = PNP_ROOT.copy()
    y_carriage_t = base_t @ translation((0.0, y, 0.0))
    x_carriage_t = y_carriage_t @ translation((x, 0.0, 0.0))
    # Only the nozzle barrel rotates - z_carriage_left/right translate only,
    # matching joint_c_left/right's real "0 0 0" origin in
    # lumenpnp_juanenpnp.urdf (the nozzle rotates about the same point its
    # z_carriage parent sits at, no extra offset).
    z_carriage_left_t = x_carriage_t @ translation((0.0, 0.0, z))
    z_carriage_right_t = x_carriage_t @ translation((0.0, 0.0, z))
    nozzle_left_t = z_carriage_left_t @ rot_z(nozzle1_deg * DEG)
    nozzle_right_t = z_carriage_right_t @ rot_z(nozzle2_deg * DEG)

    return {
        "base": base_t,
        "y_carriage": y_carriage_t,
        "x_carriage": x_carriage_t,
        "z_carriage_left": z_carriage_left_t,
        "z_carriage_right": z_carriage_right_t,
        "nozzle_left": nozzle_left_t,
        "nozzle_right": nozzle_right_t,
    }
