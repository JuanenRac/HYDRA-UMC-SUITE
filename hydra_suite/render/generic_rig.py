# =============================================================================
# HYDRA-UMC SUITE - render/generic_rig.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The "Generic (6-DOF)" fallback rig - a primitive-built (cylinders/boxes,
# no STL) placeholder for any robot model with no real mesh data, ported
# 1:1 from HYDRA-UMC-STUDIO's own src/components/3d/GenericRobotArm.tsx
# (same nested-group structure, same dimensions, same hex colors) rather
# than invented fresh, so this app's own "Generic" robot looks like the
# same robot the web UI shows for one.
#
# GenericRobotArm.tsx builds its rig as nested <group position rotation>
# elements; each SEGMENT below instead names which JOINT FRAME (0..6, see
# generic_frame_transforms()) it's attached to plus its own local
# position/rotation within that frame - same math, flattened into a table
# since this app has no JSX scene-graph nesting to lean on.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hydra_suite.render.kinematics import DEG, rot_x, rot_y, rot_z, translation

# Hex colors copied verbatim from GenericRobotArm.tsx.
COLOR_PRIMARY = (0x47 / 255, 0x55 / 255, 0x69 / 255)
COLOR_SECONDARY = (0x1A / 255, 0x20 / 255, 0x2C / 255)
COLOR_JOINT = (0x2D / 255, 0x37 / 255, 0x48 / 255)
COLOR_ACCENT = (0xCB / 255, 0xD5 / 255, 0xE1 / 255)

GENERIC_HOME_POSE_DEG = {"j1": 0.0, "j2": -45.0, "j3": 45.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}


@dataclass(frozen=True)
class Segment:
    frame: int  # which entry of generic_frame_transforms()'s own return list this attaches to
    kind: str  # "cylinder" or "box"
    # cylinder: (radius_top, radius_bottom, height) ; box: (width, height, depth)
    size: tuple[float, float, float]
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)  # local rotation, plain X/Y/Z (matches three.js rotation=[x,y,z] Euler on a <group>)
    color: tuple[float, float, float] = COLOR_PRIMARY


# Frame 0: world/base, before any joint.
# Frame 1: position=[0,0.17,0], rotation=[0,j1,0]  (shoulder swivel)
# Frame 2: frame1 -> position=[0,0.12,0] -> rotation=[0,0,j2]
# Frame 3: frame2 -> position=[0,0.16,0] -> rotation=[0,0,-j3]
# Frame 4: frame3 -> rotation=[0,j4,0]  (no extra translation - same origin as frame 3)
# Frame 5: frame4 -> position=[0,0.20,0] -> rotation=[0,0,j5]
# Frame 6: frame5 -> position=[0,0.05,0] -> rotation=[0,j6,0]
SEGMENTS: list[Segment] = [
    # Base pedestal (world frame - static, no joint rotates it).
    Segment(0, "cylinder", (0.07, 0.09, 0.04), pos=(0, 0.02, 0), color=COLOR_SECONDARY),
    Segment(0, "cylinder", (0.065, 0.07, 0.13), pos=(0, 0.105, 0), color=COLOR_SECONDARY),
    # Shoulder base swivel + offset block (rotates with j1).
    Segment(1, "cylinder", (0.065, 0.065, 0.04), pos=(0, 0.02, 0), color=COLOR_PRIMARY),
    Segment(1, "box", (0.09, 0.08, 0.10), pos=(0, 0.08, 0), color=COLOR_PRIMARY),
    # J2 motor housing + upper arm (rotates with j2).
    Segment(2, "cylinder", (0.05, 0.05, 0.12), rpy=(90 * DEG, 0, 0), color=COLOR_JOINT),
    Segment(2, "cylinder", (0.052, 0.052, 0.02), pos=(0, 0, 0.05), rpy=(90 * DEG, 0, 0), color=COLOR_ACCENT),
    Segment(2, "cylinder", (0.04, 0.05, 0.16), pos=(0, 0.08, 0), color=COLOR_PRIMARY),  # upper arm, L1=160mm
    # J3 motor housing + elbow block (rotates with j3).
    Segment(3, "cylinder", (0.045, 0.045, 0.10), rpy=(90 * DEG, 0, 0), color=COLOR_JOINT),
    Segment(3, "box", (0.06, 0.06, 0.07), color=COLOR_PRIMARY),
    # Forearm (rotates with j4, the roll joint).
    Segment(4, "cylinder", (0.035, 0.045, 0.20), pos=(0, 0.10, 0), color=COLOR_PRIMARY),  # forearm, L2=200mm
    # J5 wrist pitch housing (rotates with j5).
    Segment(5, "cylinder", (0.035, 0.035, 0.08), rpy=(90 * DEG, 0, 0), color=COLOR_JOINT),
    Segment(5, "box", (0.05, 0.05, 0.05), pos=(0, 0.025, 0), color=COLOR_PRIMARY),
    # Wrist roll / flange (rotates with j6).
    Segment(6, "cylinder", (0.03, 0.03, 0.02), pos=(0, 0.01, 0), color=COLOR_SECONDARY),
    Segment(6, "cylinder", (0.015, 0.015, 0.005), pos=(0, 0.0225, 0), color=COLOR_ACCENT),
]


def generic_frame_transforms(joints_deg: dict[str, float]) -> list[np.ndarray]:
    """The 7 joint-frame world transforms (frame 0 = world, frame 6 =
    wrist flange) SEGMENTS attach to - see the frame-by-frame breakdown
    in this module's own header comment."""
    j1 = joints_deg.get("j1", 0.0) * DEG
    j2 = joints_deg.get("j2", 0.0) * DEG
    j3 = joints_deg.get("j3", 0.0) * DEG
    j4 = joints_deg.get("j4", 0.0) * DEG
    j5 = joints_deg.get("j5", 0.0) * DEG
    j6 = joints_deg.get("j6", 0.0) * DEG

    f0 = np.eye(4, dtype=np.float64)
    f1 = f0 @ translation((0, 0.17, 0)) @ rot_y(j1)
    f2 = f1 @ translation((0, 0.12, 0)) @ rot_z(j2)
    f3 = f2 @ translation((0, 0.16, 0)) @ rot_z(-j3)
    f4 = f3 @ rot_y(j4)
    f5 = f4 @ translation((0, 0.20, 0)) @ rot_z(j5)
    f6 = f5 @ translation((0, 0.05, 0)) @ rot_y(j6)
    return [f0, f1, f2, f3, f4, f5, f6]


def segment_world_transform(frame_transforms: list[np.ndarray], seg: Segment) -> np.ndarray:
    local = translation(seg.pos) @ rot_x(seg.rpy[0]) @ rot_y(seg.rpy[1]) @ rot_z(seg.rpy[2])
    return frame_transforms[seg.frame] @ local
