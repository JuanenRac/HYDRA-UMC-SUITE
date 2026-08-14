# =============================================================================
# HYDRA-UMC SUITE - render/kinematics.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Forward kinematics for the 3D viewport - ported from HYDRA-UMC-STUDIO's
# own src/examples/urKinematicsShared.ts (same chain data, same ROS
# rpy = Rz(yaw)*Ry(pitch)*Rx(roll) composition), extended here to return
# every LINK's own world transform (not just the end-effector position
# the TS version needed for its Cartesian display) since a 3D viewport
# has to place every mesh, not just report where the tool tip ends up.
#
# Only UR5e is wired up in this first pass (see docs/ROADMAP.md) - the
# chain/mesh-offset DATA below is deliberately kept in the same shape
# HYDRA-UMC-STUDIO's own ur*Kinematics.ts files use, so porting another
# model later is copying numbers, not redesigning this module.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEG = np.pi / 180.0


@dataclass(frozen=True)
class JointStep:
    pos: tuple[float, float, float]
    rpy: tuple[float, float, float]


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
    same composition order HYDRA-UMC-STUDIO's own rosEuler() helper
    documents needing (three.js 'ZYX' intrinsic order), not the naive
    Rx*Ry*Rz a plain per-axis loop would produce."""
    roll, pitch, yaw = rpy
    return rot_z(yaw) @ rot_y(pitch) @ rot_x(roll)


def joint_transform(step: JointStep, joint_deg: float) -> np.ndarray:
    """One joint's own contribution: translate+orient into its own frame
    per <origin>, then rotate about its own local Z by the live joint
    angle - every UR e-Series joint's <axis> is (0,0,1), no exceptions
    (confirmed against the real ur_macro.xacro - see urKinematicsShared.ts's
    own header comment for the citation)."""
    return translation(step.pos) @ rpy_matrix(step.rpy) @ rot_z(joint_deg * DEG)


# --- UR5e: real chain + mesh-offset data, copied from HYDRA-UMC-STUDIO's ---
# --- own src/examples/ur5eKinematics.ts (verbatim from Universal Robots' ---
# --- own official config/ur5e/default_kinematics.yaml / visual_parameters.yaml) ---

UR5E_CHAIN: list[JointStep] = [
    JointStep((0, 0, 0.1625), (0, 0, 0)),                                            # shoulder_pan_joint
    JointStep((0, 0, 0), (1.570796327, 0, 0)),                                        # shoulder_lift_joint
    JointStep((-0.425, 0, 0), (0, 0, 0)),                                             # elbow_joint
    JointStep((-0.3922, 0, 0.1333), (0, 0, 0)),                                       # wrist_1_joint
    JointStep((0, -0.0997, 0), (1.570796327, 0, 0)),                                  # wrist_2_joint
    JointStep((0, 0.0996, 0), (1.570796326589793, 3.141592653589793, 3.141592653589793)),  # wrist_3_joint
]

# Order: base, shoulder, upper_arm, forearm, wrist_1, wrist_2, wrist_3 - each
# applied ON TOP of that link's own joint_transform (see world_link_transforms
# below), affecting only where the MESH sits, never the child joint chain.
UR5E_MESH_OFFSETS: list[JointStep] = [
    JointStep((0, 0, 0), (0, 0, np.pi)),                       # base
    JointStep((0, 0, 0), (0, 0, np.pi)),                       # shoulder
    JointStep((0, 0, 0.138), (np.pi / 2, 0, -np.pi / 2)),      # upper_arm
    JointStep((0, 0, 0.007), (np.pi / 2, 0, -np.pi / 2)),      # forearm
    JointStep((0, 0, -0.127), (np.pi / 2, 0, 0)),              # wrist_1
    JointStep((0, 0, -0.0997), (0, 0, 0)),                     # wrist_2
    JointStep((0, -0.0005, -0.0989), (np.pi / 2, 0, 0)),       # wrist_3
]

UR5E_LINK_NAMES = ("base", "shoulder", "upper_arm", "forearm", "wrist_1", "wrist_2", "wrist_3")

UR5E_HOME_POSE_DEG = {"j1": 0.0, "j2": -90.0, "j3": 0.0, "j4": -90.0, "j5": 0.0, "j6": 0.0}


def world_link_transforms(chain: list[JointStep], joints_deg: dict[str, float]) -> list[np.ndarray]:
    """Returns one 4x4 world transform per link, in the SAME order as
    UR5E_LINK_NAMES/UR5E_MESH_OFFSETS (base first, wrist_3 last) - the
    frame each link's own joint chain continues from, BEFORE that link's
    own mesh_offset is applied (see mesh_world_transforms below, which
    layers mesh_offset on top for rendering)."""
    order = ("j1", "j2", "j3", "j4", "j5", "j6")
    t = np.eye(4, dtype=np.float64)
    transforms = [t.copy()]  # base - static, no joint before it
    for step, jname in zip(chain, order):
        t = t @ joint_transform(step, joints_deg.get(jname, 0.0))
        transforms.append(t.copy())
    return transforms


def mesh_world_transforms(
    chain: list[JointStep], mesh_offsets: list[JointStep], joints_deg: dict[str, float]
) -> list[np.ndarray]:
    """The transform to actually draw each link's mesh at - world_link_transforms()
    plus that link's own mesh_offset layered on top, matching how UR's own
    official visual_parameters.yaml (and HYDRA-UMC-STUDIO's own URArm.tsx)
    apply it: a correction to where the MESH sits, that does NOT propagate
    into the next joint's own origin."""
    links = world_link_transforms(chain, joints_deg)
    return [link_t @ translation(off.pos) @ rpy_matrix(off.rpy) for link_t, off in zip(links, mesh_offsets)]
