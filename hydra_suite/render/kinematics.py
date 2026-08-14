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


@dataclass(frozen=True)
class QuatRobotConfig:
    chain: list[JointStep]
    root_axis_target: tuple[float, float, float]
    base_offset: tuple[float, float, float]
    link_names: tuple[str, ...]
    mesh_files: dict[str, str]
    home_pose_deg: dict[str, float]


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
    "Generic (6-DOF)": RobotModelEntry("generic", None, None, None, home_pose_deg={"j1": 0.0, "j2": -45.0, "j3": 45.0, "j4": 0.0, "j5": 0.0, "j6": 0.0}),
}
