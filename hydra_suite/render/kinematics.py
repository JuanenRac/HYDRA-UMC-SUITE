# =============================================================================
# HYDRA-UMC SUITE - render/kinematics.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Forward kinematics for the 3D viewport - ported from HYDRA-UMC-STUDIO's
# own src/examples/*Kinematics.ts + src/components/3d/*Arm.tsx files (same
# chain data, same ROS rpy = Rz(yaw)*Ry(pitch)*Rx(roll) composition),
# extended to return every LINK's own world transform (not just the
# end-effector position the TS versions needed for their own Cartesian
# display) since a 3D viewport has to place every mesh, not just report
# where the tool tip ends up.
#
# World convention: Y-up, matching Three.js/HYDRA-UMC-STUDIO exactly
# (not ROS's own Z-up) - every root correction below (ROOT_ALIGN target
# vectors, the UR family's own fixed -90deg-about-X root) is copied
# verbatim from the real TS source rather than re-derived, which is only
# valid if this app's own world uses the SAME up axis those numbers were
# tuned against. See viewport.py's own camera setup for the matching
# up=(0,1,0) choice.
#
# Two robot "families" exist in this ecosystem, and both are represented
# here:
#   - UR family (UR3e/5e/10e/16e/20): every joint rotates about local Z
#     after its own <origin rpy>, no per-robot root correction beyond the
#     shared Z-up->Y-up conversion, plus a separate per-LINK mesh_offset
#     (a correction to where the MESH sits, official Universal Robots
#     data). See urKinematicsShared.ts's own header for why one shared
#     engine covers all 5 UR models.
#   - "Quaternion" family (Parol6/Faze4/AR3/AR4): each joint rotates about
#     its own ARBITRARY axis (not always Z) after its own <origin rpy>,
#     and each robot needs its own once-computed ROOT correction (align
#     joint 1's own world-frame axis onto a target "up" vector) - see
#     Parol6Arm.tsx/Faze4Arm.tsx/AR3Arm.tsx/AR4Arm.tsx's own header
#     comments for the per-robot reasoning already verified there.
#     Represented here with plain 4x4 rotation matrices (Rodrigues'
#     formula for axis-angle, not a separate quaternion type) - equivalent
#     math to the TS side's THREE.Quaternion usage, fewer moving parts to
#     get wrong porting it.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

DEG = np.pi / 180.0


@dataclass(frozen=True)
class JointStep:
    pos: tuple[float, float, float]
    rpy: tuple[float, float, float]
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0)  # only meaningful for the "quaternion" family


# --- shared matrix math -----------------------------------------------------

def rot_x(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], dtype=np.float64)


def rot_y(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], dtype=np.float64)


def rot_z(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64)


def translation(p: tuple[float, float, float]) -> np.ndarray:
    m = np.eye(4, dtype=np.float64)
    m[0, 3], m[1, 3], m[2, 3] = p
    return m


def rpy_matrix(rpy: tuple[float, float, float]) -> np.ndarray:
    """ROS URDF <origin rpy="r p y"/> composes as R = Rz(yaw)*Ry(pitch)*Rx(roll) -
    same composition order every *Arm.tsx's own rosEuler()/jointQuaternion()
    helper documents needing (three.js 'ZYX' intrinsic order), not the
    naive Rx*Ry*Rz a plain per-axis loop would produce."""
    roll, pitch, yaw = rpy
    return rot_z(yaw) @ rot_y(pitch) @ rot_x(roll)


def axis_angle_matrix(axis: tuple[float, float, float], angle_rad: float) -> np.ndarray:
    """Rodrigues' rotation formula - a rotation of angle_rad about an
    arbitrary (not necessarily cardinal) axis. Mathematically equivalent
    to THREE.Quaternion.setFromAxisAngle() converted to a matrix; used
    directly as a matrix here rather than introducing a separate
    quaternion type, since every other transform in this module is
    already a 4x4 matrix."""
    v = np.array(axis, dtype=np.float64)
    norm = np.linalg.norm(v)
    if norm < 1e-12:
        return np.eye(4, dtype=np.float64)
    x, y, z = v / norm
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    C = 1 - c
    m = np.array(
        [
            [x * x * C + c, x * y * C - z * s, x * z * C + y * s, 0],
            [y * x * C + z * s, y * y * C + c, y * z * C - x * s, 0],
            [z * x * C - y * s, z * y * C + x * s, z * z * C + c, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float64,
    )
    return m


def align_vectors_matrix(a: np.ndarray, b: tuple[float, float, float]) -> np.ndarray:
    """The rotation matrix R such that R @ normalize(a) == normalize(b),
    using the shortest arc (Rodrigues' formula around their cross
    product) - equivalent to THREE.Quaternion.setFromUnitVectors(a, b).
    This is exactly how every quaternion-family robot's own ROOT
    correction is computed on the TS side (align joint 1's own
    world-frame axis onto a chosen "up" target)."""
    a = np.asarray(a, dtype=np.float64)
    a = a / np.linalg.norm(a)
    b = np.array(b, dtype=np.float64)
    b = b / np.linalg.norm(b)
    dot = float(np.dot(a, b))
    if dot > 1.0 - 1e-9:
        return np.eye(4, dtype=np.float64)
    if dot < -1.0 + 1e-9:
        # 180 degrees apart - Rodrigues' formula is singular here (the
        # cross product is zero), so pick any axis perpendicular to a.
        perp = np.cross(a, [1.0, 0.0, 0.0])
        if np.linalg.norm(perp) < 1e-6:
            perp = np.cross(a, [0.0, 1.0, 0.0])
        return axis_angle_matrix(tuple(perp), np.pi)
    v = np.cross(a, b)
    s = np.linalg.norm(v)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]], dtype=np.float64)
    r3 = np.eye(3) + vx + vx @ vx * ((1 - dot) / (s * s))
    m = np.eye(4, dtype=np.float64)
    m[:3, :3] = r3
    return m


# =============================================================================
# UR family - shared engine for UR3e/5e/10e/16e/20
# =============================================================================

# ROS is Z-up; this app's own world (matching Three.js/HYDRA-UMC-STUDIO) is
# Y-up - the same single fixed root rotation URArm.tsx's own
# <group rotation={[-Math.PI / 2, 0, 0]}> applies once, rather than
# fighting the axis convention at every joint.
UR_ROOT = rot_x(-np.pi / 2)


def ur_world_link_transforms(chain: list[JointStep], joints_deg: dict[str, float]) -> list[np.ndarray]:
    """One 4x4 world transform per link (base first, wrist_3 last, 7
    total) - the frame each link's own joint chain continues from,
    BEFORE that link's own mesh_offset is applied."""
    order = ("j1", "j2", "j3", "j4", "j5", "j6")
    t = UR_ROOT.copy()
    transforms = [t.copy()]  # base - static, no joint before it
    for step, jname in zip(chain, order):
        joint_rot = rot_z(joints_deg.get(jname, 0.0) * DEG)  # every UR joint's own axis is local Z, no exceptions
        t = t @ translation(step.pos) @ rpy_matrix(step.rpy) @ joint_rot
        transforms.append(t.copy())
    return transforms


def ur_mesh_world_transforms(
    chain: list[JointStep], mesh_offsets: list[JointStep], joints_deg: dict[str, float]
) -> list[np.ndarray]:
    """The transform to actually draw each link's mesh at - adds that
    link's own mesh_offset on top of ur_world_link_transforms(), matching
    how Universal Robots' own official visual_parameters.yaml (and
    URArm.tsx) apply it: a correction to where the MESH sits, that does
    NOT propagate into the next joint's own origin."""
    links = ur_world_link_transforms(chain, joints_deg)
    return [link_t @ translation(off.pos) @ rpy_matrix(off.rpy) for link_t, off in zip(links, mesh_offsets)]


UR5E_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.1625), (0, 0, 0)),
    JointStep((0, 0, 0), (1.570796327, 0, 0)),
    JointStep((-0.425, 0, 0), (0, 0, 0)),
    JointStep((-0.3922, 0, 0.1333), (0, 0, 0)),
    JointStep((0, -0.0997, 0), (1.570796327, 0, 0)),
    JointStep((0, 0.0996, 0), (1.570796326589793, 3.141592653589793, 3.141592653589793)),
]
UR5E_MESH_OFFSETS: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0.138), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, 0.007), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, -0.127), (np.pi / 2, 0, 0)),
    JointStep((0, 0, -0.0997), (0, 0, 0)),
    JointStep((0, -0.0005, -0.0989), (np.pi / 2, 0, 0)),
]

UR3E_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.15185), (0, 0, 0)),
    JointStep((0, 0, 0), (1.570796327, 0, 0)),
    JointStep((-0.24355, 0, 0), (0, 0, 0)),
    JointStep((-0.2132, 0, 0.13105), (0, 0, 0)),
    JointStep((0, -0.08535, 0), (1.570796327, 0, 0)),
    JointStep((0, 0.0921, 0), (1.570796326589793, 3.141592653589793, 3.141592653589793)),
]
UR3E_MESH_OFFSETS: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0.120), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, 0.027), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, -0.104), (np.pi / 2, 0, 0)),
    JointStep((0, 0, -0.08535), (0, 0, 0)),
    JointStep((0, 0, -0.0921), (np.pi / 2, 0, 0)),
]

UR10E_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.1807), (0, 0, 0)),
    JointStep((0, 0, 0), (1.570796327, 0, 0)),
    JointStep((-0.6127, 0, 0), (0, 0, 0)),
    JointStep((-0.57155, 0, 0.17415), (0, 0, 0)),
    JointStep((0, -0.11985, 0), (1.570796327, 0, 0)),
    JointStep((0, 0.11655, 0), (1.570796326589793, 3.141592653589793, 3.141592653589793)),
]
UR10E_MESH_OFFSETS: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0.1762), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, 0.0393), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, -0.135), (np.pi / 2, 0, 0)),
    JointStep((0, 0, -0.12), (0, 0, 0)),
    JointStep((0, -0.0005, -0.1168), (np.pi / 2, 0, 0)),
]

# UR16e reuses UR10e's own base/shoulder/wrist1/wrist2/wrist3 mesh_offsets
# verbatim (documented in UR10e's own official visual_parameters.yaml:
# "UR16e uses the same parts as UR10e except the upper and lower arm are
# shortened") - not a copy/paste mistake, see ur16eKinematics.ts's own
# header comment for the same note.
UR16E_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.1807), (0, 0, 0)),
    JointStep((0, 0, 0), (1.570796327, 0, 0)),
    JointStep((-0.4784, 0, 0), (0, 0, 0)),
    JointStep((-0.36, 0, 0.17415), (0, 0, 0)),
    JointStep((0, -0.11985, 0), (1.570796327, 0, 0)),
    JointStep((0, 0.11655, 0), (1.570796326589793, 3.141592653589793, 3.141592653589793)),
]
UR16E_MESH_OFFSETS: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0.1762), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, 0.0393), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, -0.135), (np.pi / 2, 0, 0)),
    JointStep((0, 0, -0.12), (0, 0, 0)),
    JointStep((0, -0.0005, -0.1168), (np.pi / 2, 0, 0)),
]

UR20_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.2363), (0, 0, 0)),
    JointStep((0, 0, 0), (1.570796327, 0, 0)),
    JointStep((-0.862, 0, 0), (0, 0, 0)),
    JointStep((-0.7287, 0, 0.201), (0, 0, 0)),
    JointStep((0, -0.1593, 0), (1.570796327, 0, 0)),
    JointStep((0, 0.1543, 0), (1.5707963265897931, 3.1415926535897931, 3.1415926535897931)),
]
UR20_MESH_OFFSETS: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0), (0, 0, np.pi)),
    JointStep((0, 0, 0.260), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, 0.043), (np.pi / 2, 0, -np.pi / 2)),
    JointStep((0, 0, -0.0775), (np.pi / 2, 0, 0)),
    JointStep((0, 0, -0.0749), (0, 0, 0)),
    JointStep((0, 0, -0.07), (np.pi / 2, 0, 0)),
]

UR_LINK_NAMES = ("base", "shoulder", "upper_arm", "forearm", "wrist_1", "wrist_2", "wrist_3")
UR_HOME_POSE_DEG = {"j1": 0.0, "j2": -90.0, "j3": 0.0, "j4": -90.0, "j5": 0.0, "j6": 0.0}
UR_MESH_FILES = {
    "base": "base.stl",
    "shoulder": "shoulder.stl",
    "upper_arm": "upperarm.stl",
    "forearm": "forearm.stl",
    "wrist_1": "wrist1.stl",
    "wrist_2": "wrist2.stl",
    "wrist_3": "wrist3.stl",
}

# xArm6/Lite6 (UFACTORY) - same "every joint is local Z" structure as the
# UR family (chain/limits copied verbatim from xarm_ros2's own
# xarm6.urdf.xacro/lite6.urdf.xacro, BSD-3-Clause - see
# assets/meshes/xarm6/ATTRIBUTION.txt), so they reuse ur_world_link_transforms/
# ur_mesh_world_transforms directly. Unlike UR's own official meshes,
# xArm6/Lite6's own <visual><origin> is (0,0,0)/(0,0,0) for every link (the
# STLs are already authored aligned to their own joint-chain frame), so
# their MESH_OFFSETS are all-identity - no per-link recentering needed.
_IDENTITY_STEP = JointStep((0, 0, 0), (0, 0, 0))

XARM6_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.267), (0, 0, 0)),
    JointStep((0, 0, 0), (-1.5708, 0, 0)),
    JointStep((0.0535, -0.2845, 0), (0, 0, 0)),
    JointStep((0.0775, 0.3425, 0), (-1.5708, 0, 0)),
    JointStep((0, 0, 0), (1.5708, 0, 0)),
    JointStep((0.076, 0.097, 0), (-1.5708, 0, 0)),
]
XARM6_MESH_OFFSETS: list[JointStep] = [_IDENTITY_STEP] * 7
XARM6_LINK_NAMES = ("base", "link1", "link2", "link3", "link4", "link5", "link6")
XARM6_MESH_FILES = {name: f"{name}.stl" for name in XARM6_LINK_NAMES}
XARM6_HOME_POSE_DEG = {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}

LITE6_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.2435), (0, 0, 0)),
    JointStep((0, 0, 0), (1.5708, -1.5708, 3.1416)),
    JointStep((0.2002, 0, 0), (-3.1416, 0, 1.5708)),
    JointStep((0.087, -0.22761, 0), (1.5708, 0, 0)),
    JointStep((0, 0, 0), (1.5708, 0, 0)),
    JointStep((0, 0.0625, 0), (-1.5708, 0, 0)),
]
LITE6_MESH_OFFSETS: list[JointStep] = [_IDENTITY_STEP] * 7
LITE6_LINK_NAMES = ("base", "link1", "link2", "link3", "link4", "link5", "link6")
LITE6_MESH_FILES = {name: f"{name}.stl" for name in LITE6_LINK_NAMES}
LITE6_HOME_POSE_DEG = {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}

# Kinova Gen2 (j2s6s200) - same "every joint is local Z" structure (chain
# copied verbatim from Kinovarobotics/kinova-ros's own
# kinova_description/urdf/j2s6s200_standalone.xacro, BSD-3-Clause - see
# assets/meshes/gen2/ATTRIBUTION.txt). Every <visual> mesh sits at its
# own link's default origin (no explicit <origin> tag = identity), so
# GEN2_MESH_OFFSETS is all-identity like xArm6/Lite6's own.
GEN2_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.15675), (0, 3.14159265359, 0)),
    JointStep((0, 0.0016, -0.11875), (-1.57079632679, 0, 3.14159265359)),
    JointStep((0, -0.410, 0), (0, 3.14159265359, 0)),
    JointStep((0, 0.2073, -0.0114), (-1.57079632679, 0, 3.14159265359)),
    JointStep((0, 0, -0.10375), (1.57079632679, 0, 3.14159265359)),
    JointStep((0, 0.10375, 0), (-1.57079632679, 0, 3.14159265359)),
]
GEN2_MESH_OFFSETS: list[JointStep] = [_IDENTITY_STEP] * 7
GEN2_LINK_NAMES = ("base", "shoulder", "arm", "forearm", "wrist_spherical_1", "wrist_spherical_2", "hand_2finger")
GEN2_MESH_FILES = {name: f"{name}.STL" for name in GEN2_LINK_NAMES}
GEN2_HOME_POSE_DEG = {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}

# AgileX PiPER - same "every joint is local Z" structure (chain copied
# verbatim from renesas-rdk/agilex_piper_arm_description's own
# urdf/reference/agilex_piper_arm_ref.urdf, Apache-2.0 per that repo's
# own package.xml license tag - see assets/meshes/piper/ATTRIBUTION.txt;
# that repo is itself explicitly derived from AgileX's own official
# agilexrobotics/piper_ros, MIT). Identity mesh offsets, same reasoning
# as Gen2/xArm6/Lite6.
PIPER_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.123), (0, 0, 0)),
    JointStep((0, 0, 0), (1.5708, -0.1359, -3.1416)),
    JointStep((0.28503, 0, 0), (0, 0, -1.7939)),
    JointStep((-0.021984, -0.25075, 0), (1.5708, 0, 0)),
    JointStep((0, 0, 0), (-1.5708, 0, 0)),
    JointStep((8.8259e-05, -0.091, 0), (1.5708, 0, 0)),
]
PIPER_MESH_OFFSETS: list[JointStep] = [_IDENTITY_STEP] * 7
PIPER_LINK_NAMES = ("base_link", "link1", "link2", "link3", "link4", "link5", "link6")
PIPER_MESH_FILES = {name: f"{name}.STL" for name in PIPER_LINK_NAMES}
PIPER_HOME_POSE_DEG = {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}

# Kinova Gen3 Lite - same "every joint is local Z" structure (chain
# copied verbatim from ros2_kortex's own gen3_lite.urdf, BSD-3-Clause -
# see assets/meshes/gen3lite/ATTRIBUTION.txt). The source URDF's own
# end_effector_link (after joint 6) has no mesh of its own - only 6 real
# link_names/mesh_files are given here, and ur_world_link_transforms()
# returns 7 transforms; zip() truncates to the shorter list, so the
# trailing virtual-frame transform is simply never drawn (unlike the TS
# side's URArm.tsx, whose fixed-depth-6 recursion needed a 7th mesh
# entry duplicated instead - each platform's own natural mechanism for
# the same real gap).
GEN3LITE_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.12825), (0, 0, 0)),
    JointStep((0, -0.03, 0.115), (1.5708, 0, 0)),
    JointStep((0, 0.28, 0), (-3.1416, 0, 0)),
    JointStep((0, -0.14, 0.02), (1.5708, 0, 0)),
    JointStep((0.0285, 0, 0.105), (0, 1.5708, 0)),
    JointStep((-0.105, 0, 0.0285), (0, -1.5708, 0)),
]
GEN3LITE_MESH_OFFSETS: list[JointStep] = [_IDENTITY_STEP] * 6
GEN3LITE_LINK_NAMES = ("base_link", "shoulder_link", "arm_link", "forearm_link", "lower_wrist_link", "upper_wrist_link")
GEN3LITE_MESH_FILES = {name: f"{name}.STL" for name in GEN3LITE_LINK_NAMES}
GEN3LITE_HOME_POSE_DEG = {"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}


# =============================================================================
# "Quaternion" family - Parol6, Faze4, AR3, AR4 (each hand-transcribed from
# its own real URDF, arbitrary per-joint axes)
# =============================================================================

def quat_family_link_transforms(
    chain: list[JointStep], root_axis_target: tuple[float, float, float], base_offset: tuple[float, float, float], joints_deg: dict[str, float]
) -> list[np.ndarray]:
    """One 4x4 world transform per link (base first, link 6 last, 7
    total). base_offset and the ROOT alignment are applied exactly like
    the TS side's own `<group position={BASE_OFFSET}><group
    quaternion={ROOT_QUAT}>...` nesting: base_offset is the OUTERMOST
    transform, ROOT next, then the real joint chain."""
    order = ("j1", "j2", "j3", "j4", "j5", "j6")
    chain0 = chain[0]
    axis_world = (rpy_matrix(chain0.rpy)[:3, :3] @ np.array(chain0.axis, dtype=np.float64))
    root = align_vectors_matrix(axis_world, root_axis_target)
    base = translation(base_offset) @ root

    t = base.copy()
    transforms = [t.copy()]  # base_link - static, no joint before it
    for step, jname in zip(chain, order):
        spin = axis_angle_matrix(step.axis, joints_deg.get(jname, 0.0) * DEG)
        t = t @ translation(step.pos) @ rpy_matrix(step.rpy) @ spin
        transforms.append(t.copy())
    return transforms


def quat_family_mesh_world_transforms(
    chain: list[JointStep],
    mesh_offsets: list[JointStep] | None,
    root_axis_target: tuple[float, float, float],
    base_offset: tuple[float, float, float],
    joints_deg: dict[str, float],
) -> list[np.ndarray]:
    """Same as quat_family_link_transforms(), plus a per-link mesh_offset
    on top (mirrors ur_mesh_world_transforms()'s own two-layer split) -
    needed for robots like ViperX 300/WidowX 250, whose own official URDF
    gives each mesh a real <visual><origin> distinct from the joint
    chain's own origin (unlike Parol6/Faze4/AR3/AR4/e.DO/M-710iC, whose
    meshes sit directly at their own joint's frame with no separate
    offset). mesh_offsets=None (every robot before ViperX 300) is
    equivalent to passing all-identity offsets - the caller doesn't need
    to know or care which case its own robot is."""
    links = quat_family_link_transforms(chain, root_axis_target, base_offset, joints_deg)
    offsets = mesh_offsets if mesh_offsets is not None else [_IDENTITY_STEP] * len(links)
    return [link_t @ translation(off.pos) @ rpy_matrix(off.rpy) for link_t, off in zip(links, offsets)]


@dataclass(frozen=True)
class QuatRobotConfig:
    chain: list[JointStep]
    root_axis_target: tuple[float, float, float]
    base_offset: tuple[float, float, float]
    link_names: tuple[str, ...]
    mesh_files: dict[str, str]
    home_pose_deg: dict[str, float]
    # None (the default, every robot before ViperX 300/WidowX 250) means
    # "each mesh sits directly at its own joint's frame" - see
    # quat_family_mesh_world_transforms()'s own header for why some
    # robots need a real, non-identity value here instead.
    mesh_offsets: list[JointStep] | None = None


PAROL6_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, 0), (0, 0, 1)),
    JointStep((0.0234207210610375, 0, 0.1105), (-1.5707963267949, 0, 0), (0, 0, 1)),
    JointStep((0, -0.18, 0), (3.1416, 0, -1.5708), (0, 0, -1)),
    JointStep((0.0435, 0, 0), (1.5707963267949, 0, 3.14159265358979), (0, 0, -1)),
    JointStep((0, 0, -0.17635), (-1.5708, 0, 0), (0, 0, -1)),
    JointStep((0, 0, 0), (1.5708, 0, 0), (0, 0, -1)),
]
PAROL6 = QuatRobotConfig(
    chain=PAROL6_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0637, 0.0, -0.0035),
    link_names=("base_link", "L1", "L2", "L3", "L4", "L5", "L6"),
    mesh_files={"base_link": "base_link.STL", "L1": "L1.STL", "L2": "L2.STL", "L3": "L3.STL", "L4": "L4.STL", "L5": "L5.STL", "L6": "L6.STL"},
    home_pose_deg={"j1": 0.0, "j2": -25.0, "j3": 20.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

FAZE4_CHAIN: list[JointStep] = [
    JointStep((0.075629, -0.21266, 0.050734), (-1.5708, 0, -1.5708), (0, -1, 0)),
    JointStep((0, -0.20182, 0), (0, 0, -1.8111), (0, 0, 1)),
    JointStep((0.32, 0, 0), (3.1416, 0, -1.1753), (0, 0, -1)),
    JointStep((0, -0.0735, 0), (-0.5648, -0.78173, 1.7809), (0.14804, 0.90477, 0.39934)),
    JointStep((0.037114, 0.22683, 0.10011), (2.2965, -0.74045, -0.57161), (-1, 0, 0)),
    JointStep((0, 0, -0.042312), (-3.1416, 0, 0.2419), (0, 0, 1)),
]
FAZE4 = QuatRobotConfig(
    chain=FAZE4_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(-0.0756, -0.0157, -0.1697),
    link_names=("base_link", "rotary_base", "nadlaktica", "lakat", "podlaktica", "saka", "hvataljka"),
    mesh_files={
        "base_link": "base_link.STL",
        "rotary_base": "rotary_base.STL",
        "nadlaktica": "nadlaktica.STL",
        "lakat": "lakat.STL",
        "podlaktica": "podlaktica.STL",
        "saka": "saka.STL",
        "hvataljka": "hvataljka.STL",
    },
    home_pose_deg={"j1": 0.0, "j2": -20.0, "j3": 15.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

AR3_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.003445), (3.1416, 0, 0), (0, 0, 1)),
    JointStep((0, 0.064146, -0.16608), (1.5708, 0.5236, -1.5708), (0, 0, -1)),
    JointStep((0.1525, -0.26414, 0), (0, 0, -1.4953816339), (0, 0, -1)),
    JointStep((0, 0, 0.00675), (1.5708, -1.2554, -1.5708), (0, 0, -1)),
    JointStep((0, 0, -0.22225), (3.1416, 0, -2.8262), (-1, 0, 0)),
    JointStep((-0.000294, 0, 0.02117), (0, 0, 3.1416), (0, 0, 1)),
]
AR3 = QuatRobotConfig(
    chain=AR3_CHAIN,
    root_axis_target=(0.0, -1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0477),
    link_names=("base_link", "link_1", "link_2", "link_3", "link_4", "link_5", "link_6"),
    mesh_files={
        "base_link": "base_link.STL",
        "link_1": "link_1.STL",
        "link_2": "link_2.STL",
        "link_3": "link_3.STL",
        "link_4": "link_4.STL",
        "link_5": "link_5.STL",
        "link_6": "link_6.STL",
    },
    home_pose_deg={"j1": 0.0, "j2": -60.0, "j3": 60.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

AR4_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.092), (3.1416, 0, 0), (0, 0, 1)),
    JointStep((0, 0.06415, -0.07778), (1.5708, 0, -1.5708), (0, 0, -1)),
    JointStep((0, -0.305, 0), (0, 0, 3.1416), (0, 0, -1)),
    JointStep((0, 0, 0), (1.5708, 0, -1.5708), (0, 0, -1)),
    JointStep((0, 0, -0.22294), (3.1416, 0, -1.5708), (1, 0, 0)),
    JointStep((0, 0, 0.041), (0, 0, 0), (0, 0, 1)),
]
AR4 = QuatRobotConfig(
    chain=AR4_CHAIN,
    root_axis_target=(0.0, -1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0477),
    link_names=("base_link", "link_1", "link_2", "link_3", "link_4", "link_5", "link_6"),
    mesh_files={
        "base_link": "base_link.STL",
        "link_1": "link_1.STL",
        "link_2": "link_2.STL",
        "link_3": "link_3.STL",
        "link_4": "link_4.STL",
        "link_5": "link_5.STL",
        "link_6": "link_6.STL",
    },
    home_pose_deg={"j1": 0.0, "j2": 40.0, "j3": -30.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

# e.DO (Comau) - unlike xArm6/Lite6, every joint's own <axis> here is
# genuinely arbitrary (joint_2's own axis is (-0.88847,0.2908,0.35504),
# not a cardinal direction) - chain copied verbatim from
# eDO_description's own robots/edo_sim.urdf (BSD-3-Clause, Comau S.p.A -
# see assets/meshes/edo/ATTRIBUTION.txt), so this uses the same
# quaternion-family engine as Parol6/Faze4/AR3/AR4. base_link's own STL
# origin is (0,0,0) in the source URDF, so base_offset is (0,0,0) - no
# hand-tuned recentering needed (unlike Parol6/Faze4's own off-center meshes).
EDO_CHAIN: list[JointStep] = [
    JointStep((0.057188, 0.0059831, 0.13343), (1.5708, 6.9389e-16, -3.1416), (0, 1, 0)),
    JointStep((0, 0.18967, 0), (0.94237, -0.4634, -0.11653), (-0.88847, 0.2908, 0.35504)),
    JointStep((-0.024558, 0.12737, -0.16578), (0.97336, -0.36296, 2.8253), (1, 0, 0)),
    JointStep((0.0088, -0.1588, 0), (-1.5708, 0, 0), (0, 0, -1)),
    JointStep((0, 0, -0.1053), (3.1416, 1.1102e-14, 3.1416), (-1, 0, 0)),
    JointStep((-0.0039, 0, 0.1636), (-1.5708, 1.249e-14, 0), (0, -1, 0)),
]
EDO = QuatRobotConfig(
    chain=EDO_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0),
    link_names=("base_link", "link_1", "link_2", "link_3", "link_4", "link_5", "link_6"),
    mesh_files={
        "base_link": "base_link.STL",
        "link_1": "link_1.STL",
        "link_2": "link_2.STL",
        "link_3": "link_3.STL",
        "link_4": "link_4.STL",
        "link_5": "link_5.STL",
        "link_6": "link_6.STL",
    },
    home_pose_deg={"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

# FANUC M-710iC - every joint's own <origin rpy> is (0,0,0) (pure
# translation between joints) but the per-joint axis varies (not always
# Z: joint_2 is world Y, joint_4/joint_6 are -X) - chain copied verbatim
# from robot-descriptions/fanuc_m710ic_description's own urdf/
# m710ic70.urdf (BSD-3-Clause - see assets/meshes/m710ic/ATTRIBUTION.txt).
M710IC_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.565), (0, 0, 0), (0, 0, 1)),
    JointStep((0.150, 0, 0), (0, 0, 0), (0, 1, 0)),
    JointStep((0, 0, 0.870), (0, 0, 0), (0, -1, 0)),
    JointStep((0, 0, 0.170), (0, 0, 0), (-1, 0, 0)),
    JointStep((1.016, 0, 0), (0, 0, 0), (0, -1, 0)),
    JointStep((0.175, 0, 0), (0, 0, 0), (-1, 0, 0)),
]
M710IC = QuatRobotConfig(
    chain=M710IC_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0),
    link_names=("base_link", "link_1", "link_2", "link_3", "link_4", "link_5", "link_6"),
    mesh_files={
        "base_link": "base_link.stl",
        "link_1": "link_1.stl",
        "link_2": "link_2.stl",
        "link_3": "link_3.stl",
        "link_4": "link_4.stl",
        "link_5": "link_5.stl",
        "link_6": "link_6.stl",
    },
    home_pose_deg={"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

# SO-ARM100 (The Robot Studio) - chain copied verbatim from that
# repository's own Simulation/SO100/so100.urdf (Apache-2.0 - see
# assets/meshes/so100/ATTRIBUTION.txt). ONLY 5 real arm joints (not 6 -
# the source URDF's own 6th joint is the gripper jaw, not a wrist
# orientation axis) - see that ATTRIBUTION.txt for why j6 is left unused
# rather than repurposed. quat_family_link_transforms()'s own `order`
# tuple is j1..j6, but zip(chain, order) truncates to the chain's actual
# length (5 here), so this "just works" with a 5-entry chain - same
# zip-truncation mechanism GEN3LITE_CHAIN's own comment already
# documents, no engine change needed.
SOARM100_CHAIN: list[JointStep] = [
    JointStep((0, -0.0452, 0.0165), (1.57079, 0, 0), (0, 1, 0)),
    JointStep((0, 0.1025, 0.0306), (-1.8, 0, 0), (1, 0, 0)),
    JointStep((0, 0.11257, 0.028), (1.57079, 0, 0), (1, 0, 0)),
    JointStep((0, 0.0052, 0.1349), (-1, 0, 0), (1, 0, 0)),
    JointStep((0, -0.0601, 0), (0, 1.57079, 0), (0, 1, 0)),
]
SOARM100 = QuatRobotConfig(
    chain=SOARM100_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0),
    link_names=("base", "shoulder", "upper_arm", "lower_arm", "wrist", "gripper"),
    mesh_files={
        "base": "Base.stl",
        "shoulder": "Rotation_Pitch.stl",
        "upper_arm": "Upper_Arm.stl",
        "lower_arm": "Lower_Arm.stl",
        "wrist": "Wrist_Pitch_Roll.stl",
        "gripper": "Fixed_Jaw.stl",
    },
    home_pose_deg={"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

# Koch v1.1 / "Low-Cost Robot Arm" (same real open-hardware design, see
# assets/meshes/koch/ATTRIBUTION.txt for why this ports it once instead
# of as two near-duplicate robots) - chain copied verbatim from
# mujoco_menagerie's own low_cost_robot_arm/low_cost_robot_arm.xml MJCF
# (Apache-2.0). Only 5 real arm joints (not 6 - the source MJCF's own
# 6th joint is the gripper jaw), same situation as SO-ARM100.
KOCH_CHAIN: list[JointStep] = [
    JointStep((0.012, 0, 0.0409), (0, 0, 0), (0, 0, -1)),
    JointStep((0, -0.0209, 0.0154), (0, 0, 0), (0, 1, 0)),
    JointStep((-0.0148, 0.0065, 0.1083), (0, 0, 0), (0, -1, 0)),
    JointStep((-0.10048, 5e-05, 0.0026999), (0, 0, 0), (0, 1, 0)),
    JointStep((-0.045, 0.013097, 0), (0, 0, 0), (1, 0, 0)),
]
KOCH = QuatRobotConfig(
    chain=KOCH_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0),
    link_names=("base_link", "shoulder_rotation", "shoulder_to_elbow", "elbow_to_wrist_extension", "elbow_to_wrist", "gripper_static_finger"),
    mesh_files={
        "base_link": "base_link.stl",
        "shoulder_rotation": "shoulder_rotation.stl",
        "shoulder_to_elbow": "shoulder_to_elbow.stl",
        "elbow_to_wrist_extension": "elbow_to_wrist_extension.stl",
        "elbow_to_wrist": "elbow_to_wrist.stl",
        "gripper_static_finger": "gripper_static_finger.stl",
    },
    home_pose_deg={"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
)

# Universal Robots UR3/UR5/UR10 (classic, pre-e-Series) - chains built
# from ros-industrial/universal_robot's own real DH parameters
# (BSD-3-Clause - see assets/meshes/ur{3,5,10}classic/ATTRIBUTION.txt).
# UNLIKE the e-Series (UR3E_CHAIN etc. above, all local-Z), this classic
# generation's own DH-based URDF mixes axes per joint (shoulder_pan/
# wrist_2 = Z, shoulder_lift/elbow/wrist_1/wrist_3 = Y) - so despite
# being a Universal Robots product, these use the "quaternion family"
# engine, not ur_world_link_transforms(). Mesh files reuse the exact
# same names as the e-Series (base/shoulder/upperarm/forearm/wrist1/2/3
# .stl) since UR kept that naming convention across both generations.
_UR_CLASSIC_LINK_NAMES = ("base_link", "shoulder_link", "upper_arm_link", "forearm_link", "wrist_1_link", "wrist_2_link", "wrist_3_link")
_UR_CLASSIC_MESH_FILES = {
    "base_link": "base.stl", "shoulder_link": "shoulder.stl", "upper_arm_link": "upperarm.stl",
    "forearm_link": "forearm.stl", "wrist_1_link": "wrist1.stl", "wrist_2_link": "wrist2.stl", "wrist_3_link": "wrist3.stl",
}
_UR_CLASSIC_HOME_POSE_DEG = {"j1": 0.0, "j2": -90.0, "j3": 0.0, "j4": -90.0, "j5": 0.0, "j6": 0.0}

UR3CLASSIC_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.1519), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0.1198, 0), (0, np.pi / 2, 0), (0, 1, 0)),
    JointStep((0, -0.0925, 0.24365), (0, 0, 0), (0, 1, 0)),
    JointStep((0, 0, 0.21325), (0, np.pi / 2, 0), (0, 1, 0)),
    JointStep((0, 0.08505, 0), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0, 0.08535), (0, 0, 0), (0, 1, 0)),
]
UR3CLASSIC = QuatRobotConfig(
    chain=UR3CLASSIC_CHAIN, root_axis_target=(0.0, 1.0, 0.0), base_offset=(0.0, 0.0, 0.0),
    link_names=_UR_CLASSIC_LINK_NAMES, mesh_files=_UR_CLASSIC_MESH_FILES, home_pose_deg=_UR_CLASSIC_HOME_POSE_DEG,
)

UR5CLASSIC_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.089159), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0.13585, 0), (0, np.pi / 2, 0), (0, 1, 0)),
    JointStep((0, -0.1197, 0.425), (0, 0, 0), (0, 1, 0)),
    JointStep((0, 0, 0.39225), (0, np.pi / 2, 0), (0, 1, 0)),
    JointStep((0, 0.093, 0), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0, 0.09465), (0, 0, 0), (0, 1, 0)),
]
UR5CLASSIC = QuatRobotConfig(
    chain=UR5CLASSIC_CHAIN, root_axis_target=(0.0, 1.0, 0.0), base_offset=(0.0, 0.0, 0.0),
    link_names=_UR_CLASSIC_LINK_NAMES, mesh_files=_UR_CLASSIC_MESH_FILES, home_pose_deg=_UR_CLASSIC_HOME_POSE_DEG,
)

UR10CLASSIC_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.1273), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0.220941, 0), (0, np.pi / 2, 0), (0, 1, 0)),
    JointStep((0, -0.1719, 0.612), (0, 0, 0), (0, 1, 0)),
    JointStep((0, 0, 0.5723), (0, np.pi / 2, 0), (0, 1, 0)),
    JointStep((0, 0.1149, 0), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0, 0.1157), (0, 0, 0), (0, 1, 0)),
]
UR10CLASSIC = QuatRobotConfig(
    chain=UR10CLASSIC_CHAIN, root_axis_target=(0.0, 1.0, 0.0), base_offset=(0.0, 0.0, 0.0),
    link_names=_UR_CLASSIC_LINK_NAMES, mesh_files=_UR_CLASSIC_MESH_FILES, home_pose_deg=_UR_CLASSIC_HOME_POSE_DEG,
)

# Unitree Z1 - every joint's own rpy is (0,0,0) (pure translation) but
# the axis varies per joint (not always Z) - chain copied verbatim from
# mujoco_menagerie's own unitree_z1/z1.xml MJCF (BSD-3-Clause, Unitree
# Robotics - see assets/meshes/z1/ATTRIBUTION.txt). MJCF bodies have no
# separate visual-mesh offset from their own joint frame here (no <geom
# quat/pos> override beyond the body's own placement), so identity mesh
# offsets, same as the other quat-family robots without one.
Z1_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.0585), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0, 0.045), (0, 0, 0), (0, 1, 0)),
    JointStep((-0.35, 0, 0), (0, 0, 0), (0, 1, 0)),
    JointStep((0.218, 0, 0.057), (0, 0, 0), (0, 1, 0)),
    JointStep((0.07, 0, 0), (0, 0, 0), (0, 0, 1)),
    JointStep((0.0492, 0, 0), (0, 0, 0), (1, 0, 0)),
]
Z1 = QuatRobotConfig(
    chain=Z1_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0),
    link_names=("link00", "link01", "link02", "link03", "link04", "link05", "link06"),
    mesh_files={
        "link00": "z1_Link00.stl",
        "link01": "z1_Link01.stl",
        "link02": "z1_Link02.stl",
        "link03": "z1_Link03.stl",
        "link04": "z1_Link04.stl",
        "link05": "z1_Link05.stl",
        "link06": "z1_Link06.stl",
    },
    # From the source MJCF's own <keyframe> "home" qpos (0, 0.785, -0.261, -0.523, 0, 0) rad.
    home_pose_deg={"j1": 0.0, "j2": 44.98, "j3": -14.96, "j4": -29.97, "j5": 0.0, "j6": 0.0},
)

# ViperX 300 / WidowX 250 (Trossen Robotics) - chains copied verbatim
# from Interbotix's own official interbotix_ros_manipulators repo
# (BSD-3-Clause - see assets/meshes/vx300s|wx250s/ATTRIBUTION.txt).
# Unlike every other quat-family robot so far, these DO have a real,
# non-identity <visual><origin> per link, distinct from the joint
# chain's own origin - hence VX300S_MESH_OFFSETS/WX250S_MESH_OFFSETS
# below (see quat_family_mesh_world_transforms()'s own header for why
# that function exists). Both robots share the exact same rig design
# (same mesh-offset pattern, just different link lengths) - Trossen's
# smaller sibling product in the same arm family.
VX300S_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.079), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0, 0.04805), (0, 0, 0), (0, 1, 0)),
    JointStep((0.05955, 0, 0.3), (0, 0, 0), (0, 1, 0)),
    JointStep((0.2, 0, 0), (0, 0, 0), (1, 0, 0)),
    JointStep((0.1, 0, 0), (0, 0, 0), (0, 1, 0)),
    JointStep((0.069744, 0, 0), (0, 0, 0), (1, 0, 0)),
]
_TROSSEN_MESH_OFFSETS: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, 1.5708)),
    JointStep((0, 0, -0.003), (0, 0, 1.5708)),
    JointStep((0, 0, 0), (0, 0, 1.5708)),
    JointStep((0, 0, 0), (0, 0, 0)),
    JointStep((0, 0, 0), (3.1416, 0, 0)),
    JointStep((0, 0, 0), (0, 0, 1.5708)),
    JointStep((-0.02, 0, 0), (0, 0, 1.5708)),
]
VX300S = QuatRobotConfig(
    chain=VX300S_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0),
    link_names=("base_link", "shoulder_link", "upper_arm_link", "upper_forearm_link", "lower_forearm_link", "wrist_link", "gripper_link"),
    mesh_files={
        "base_link": "vx300s_1_base.stl",
        "shoulder_link": "vx300s_2_shoulder.stl",
        "upper_arm_link": "vx300s_3_upper_arm.stl",
        "upper_forearm_link": "vx300s_4_upper_forearm.stl",
        "lower_forearm_link": "vx300s_5_lower_forearm.stl",
        "wrist_link": "vx300s_6_wrist.stl",
        "gripper_link": "vx300s_7_gripper.stl",
    },
    home_pose_deg={"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
    mesh_offsets=_TROSSEN_MESH_OFFSETS,
)

WX250S_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.072), (0, 0, 0), (0, 0, 1)),
    JointStep((0, 0, 0.03865), (0, 0, 0), (0, 1, 0)),
    JointStep((0.04975, 0, 0.25), (0, 0, 0), (0, 1, 0)),
    JointStep((0.175, 0, 0), (0, 0, 0), (1, 0, 0)),
    JointStep((0.075, 0, 0), (0, 0, 0), (0, 1, 0)),
    JointStep((0.065, 0, 0), (0, 0, 0), (1, 0, 0)),
]
WX250S = QuatRobotConfig(
    chain=WX250S_CHAIN,
    root_axis_target=(0.0, 1.0, 0.0),
    base_offset=(0.0, 0.0, 0.0),
    link_names=("base_link", "shoulder_link", "upper_arm_link", "upper_forearm_link", "lower_forearm_link", "wrist_link", "gripper_link"),
    mesh_files={
        "base_link": "wx250s_1_base.stl",
        "shoulder_link": "wx250s_2_shoulder.stl",
        "upper_arm_link": "wx250s_3_upper_arm.stl",
        "upper_forearm_link": "wx250s_4_upper_forearm.stl",
        "lower_forearm_link": "wx250s_5_lower_forearm.stl",
        "wrist_link": "wx250s_6_wrist.stl",
        "gripper_link": "wx250s_7_gripper.stl",
    },
    home_pose_deg={"j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0, "j5": 0.0, "j6": 0.0},
    mesh_offsets=_TROSSEN_MESH_OFFSETS,
)


# =============================================================================
# Robot registry - one entry per robot.model string HYDRA-UMC-STUDIO's own
# store.tsx RobotModel type uses verbatim (see src/store.tsx's own
# RobotModel union and src/components/3d/RobotArm.tsx's own switch), so a
# RobotView.model straight off the wire looks itself up here with no
# separate name-mapping table to keep in sync.
# =============================================================================
@dataclass(frozen=True)
class RobotModelEntry:
    family: str  # "ur" | "quat" | "generic"
    mesh_dir: str | None  # under assets/meshes/ - None for "generic" (no STL)
    link_names: tuple[str, ...] | None
    mesh_files: dict[str, str] | None
    chain: list[JointStep] | None = None  # "ur" family
    mesh_offsets: list[JointStep] | None = None  # "ur" family
    quat_config: QuatRobotConfig | None = None  # "quat" family
    home_pose_deg: dict[str, float] = field(default_factory=dict)


ROBOT_REGISTRY: dict[str, RobotModelEntry] = {
    "UR3e (6-DOF)": RobotModelEntry("ur", "ur3e", UR_LINK_NAMES, UR_MESH_FILES, chain=UR3E_CHAIN, mesh_offsets=UR3E_MESH_OFFSETS, home_pose_deg=UR_HOME_POSE_DEG),
    "UR5e (6-DOF)": RobotModelEntry("ur", "ur5e", UR_LINK_NAMES, UR_MESH_FILES, chain=UR5E_CHAIN, mesh_offsets=UR5E_MESH_OFFSETS, home_pose_deg=UR_HOME_POSE_DEG),
    "UR10e (6-DOF)": RobotModelEntry("ur", "ur10e", UR_LINK_NAMES, UR_MESH_FILES, chain=UR10E_CHAIN, mesh_offsets=UR10E_MESH_OFFSETS, home_pose_deg=UR_HOME_POSE_DEG),
    "UR16e (6-DOF)": RobotModelEntry("ur", "ur16e", UR_LINK_NAMES, UR_MESH_FILES, chain=UR16E_CHAIN, mesh_offsets=UR16E_MESH_OFFSETS, home_pose_deg=UR_HOME_POSE_DEG),
    "UR20 (6-DOF)": RobotModelEntry("ur", "ur20", UR_LINK_NAMES, UR_MESH_FILES, chain=UR20_CHAIN, mesh_offsets=UR20_MESH_OFFSETS, home_pose_deg=UR_HOME_POSE_DEG),
    "Parol6 (6-DOF)": RobotModelEntry("quat", "parol6", PAROL6.link_names, PAROL6.mesh_files, quat_config=PAROL6, home_pose_deg=PAROL6.home_pose_deg),
    "Faze4 (6-DOF)": RobotModelEntry("quat", "faze4", FAZE4.link_names, FAZE4.mesh_files, quat_config=FAZE4, home_pose_deg=FAZE4.home_pose_deg),
    "AR3 (6-DOF)": RobotModelEntry("quat", "ar3", AR3.link_names, AR3.mesh_files, quat_config=AR3, home_pose_deg=AR3.home_pose_deg),
    "AR4 (6-DOF)": RobotModelEntry("quat", "ar4", AR4.link_names, AR4.mesh_files, quat_config=AR4, home_pose_deg=AR4.home_pose_deg),
    "xArm6 (6-DOF)": RobotModelEntry("ur", "xarm6", XARM6_LINK_NAMES, XARM6_MESH_FILES, chain=XARM6_CHAIN, mesh_offsets=XARM6_MESH_OFFSETS, home_pose_deg=XARM6_HOME_POSE_DEG),
    "Lite 6 (6-DOF)": RobotModelEntry("ur", "lite6", LITE6_LINK_NAMES, LITE6_MESH_FILES, chain=LITE6_CHAIN, mesh_offsets=LITE6_MESH_OFFSETS, home_pose_deg=LITE6_HOME_POSE_DEG),
    "e.DO (6-DOF)": RobotModelEntry("quat", "edo", EDO.link_names, EDO.mesh_files, quat_config=EDO, home_pose_deg=EDO.home_pose_deg),
    "Gen3 Lite (6-DOF)": RobotModelEntry("ur", "gen3lite", GEN3LITE_LINK_NAMES, GEN3LITE_MESH_FILES, chain=GEN3LITE_CHAIN, mesh_offsets=GEN3LITE_MESH_OFFSETS, home_pose_deg=GEN3LITE_HOME_POSE_DEG),
    "M-710iC (6-DOF)": RobotModelEntry("quat", "m710ic", M710IC.link_names, M710IC.mesh_files, quat_config=M710IC, home_pose_deg=M710IC.home_pose_deg),
    "SO-ARM100 (5-DOF)": RobotModelEntry("quat", "so100", SOARM100.link_names, SOARM100.mesh_files, quat_config=SOARM100, home_pose_deg=SOARM100.home_pose_deg),
    "Gen2 (6-DOF)": RobotModelEntry("ur", "gen2", GEN2_LINK_NAMES, GEN2_MESH_FILES, chain=GEN2_CHAIN, mesh_offsets=GEN2_MESH_OFFSETS, home_pose_deg=GEN2_HOME_POSE_DEG),
    "PiPER (6-DOF)": RobotModelEntry("ur", "piper", PIPER_LINK_NAMES, PIPER_MESH_FILES, chain=PIPER_CHAIN, mesh_offsets=PIPER_MESH_OFFSETS, home_pose_deg=PIPER_HOME_POSE_DEG),
    "Z1 (6-DOF)": RobotModelEntry("quat", "z1", Z1.link_names, Z1.mesh_files, quat_config=Z1, home_pose_deg=Z1.home_pose_deg),
    "ViperX 300 (6-DOF)": RobotModelEntry("quat", "vx300s", VX300S.link_names, VX300S.mesh_files, quat_config=VX300S, home_pose_deg=VX300S.home_pose_deg),
    "WidowX 250 (6-DOF)": RobotModelEntry("quat", "wx250s", WX250S.link_names, WX250S.mesh_files, quat_config=WX250S, home_pose_deg=WX250S.home_pose_deg),
    "Koch v1.1 (5-DOF)": RobotModelEntry("quat", "koch", KOCH.link_names, KOCH.mesh_files, quat_config=KOCH, home_pose_deg=KOCH.home_pose_deg),
    "UR3 (6-DOF)": RobotModelEntry("quat", "ur3classic", UR3CLASSIC.link_names, UR3CLASSIC.mesh_files, quat_config=UR3CLASSIC, home_pose_deg=UR3CLASSIC.home_pose_deg),
    "UR5 (6-DOF)": RobotModelEntry("quat", "ur5classic", UR5CLASSIC.link_names, UR5CLASSIC.mesh_files, quat_config=UR5CLASSIC, home_pose_deg=UR5CLASSIC.home_pose_deg),
    "UR10 (6-DOF)": RobotModelEntry("quat", "ur10classic", UR10CLASSIC.link_names, UR10CLASSIC.mesh_files, quat_config=UR10CLASSIC, home_pose_deg=UR10CLASSIC.home_pose_deg),
    "Generic (6-DOF)": RobotModelEntry("generic", None, None, None, home_pose_deg={"j1": 0.0, "j2": -45.0, "j3": 45.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}),
}
