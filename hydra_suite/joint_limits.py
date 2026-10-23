# =============================================================================
# HYDRA-UMC SUITE - joint_limits.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The range of every joint of the models that have a published one, in degrees, the
# same table HYDRA-UMC-STUDIO uses to clamp its own jog (so a slider can never ask a
# joint for more than the robot can turn). A model without an entry gets the generic
# -180..180 range.
# =============================================================================
from __future__ import annotations

GENERIC_RANGE_DEG: tuple[float, float] = (-180.0, 180.0)

JOINT_LIMITS_DEG: dict[str, dict[str, tuple[float, float]]] = {
    "Parol6 (6-DOF)": {
        "j1": (-97.4, 187.4),
        "j2": (-56.15, 57.3),
        "j3": (-114.59, 74.48),
        "j4": (-114.59, 114.59),
        "j5": (-120.32, 120.32),
        "j6": (-177.62, 177.62),
    },
    "AR4 (6-DOF)": {
        "j1": (-170.0, 170.0),
        "j2": (-42.0, 90.0),
        "j3": (-89.0, 52.0),
        "j4": (-180.0, 180.0),
        "j5": (-105.0, 105.0),
        "j6": (-180.0, 180.0),
    },
    "UR3e (6-DOF)": {
        "j1": (-360.0, 360.0),
        "j2": (-360.0, 360.0),
        "j3": (-180.0, 180.0),
        "j4": (-360.0, 360.0),
        "j5": (-360.0, 360.0),
        "j6": (-180.0, 180.0),
    },
    "UR5e (6-DOF)": {
        "j1": (-360.0, 360.0),
        "j2": (-360.0, 360.0),
        "j3": (-180.0, 180.0),
        "j4": (-360.0, 360.0),
        "j5": (-360.0, 360.0),
        "j6": (-180.0, 180.0),
    },
    "UR10e (6-DOF)": {
        "j1": (-360.0, 360.0),
        "j2": (-360.0, 360.0),
        "j3": (-180.0, 180.0),
        "j4": (-360.0, 360.0),
        "j5": (-360.0, 360.0),
        "j6": (-180.0, 180.0),
    },
    "UR16e (6-DOF)": {
        "j1": (-360.0, 360.0),
        "j2": (-360.0, 360.0),
        "j3": (-180.0, 180.0),
        "j4": (-360.0, 360.0),
        "j5": (-360.0, 360.0),
        "j6": (-180.0, 180.0),
    },
    "UR20 (6-DOF)": {
        "j1": (-360.0, 360.0),
        "j2": (-360.0, 360.0),
        "j3": (-180.0, 180.0),
        "j4": (-360.0, 360.0),
        "j5": (-360.0, 360.0),
        "j6": (-180.0, 180.0),
    },
    "xArm6 (6-DOF)": {
        "j1": (-360.0, 360.0),
        "j2": (-118.0, 120.0),
        "j3": (-225.0, 11.0),
        "j4": (-360.0, 360.0),
        "j5": (-97.0, 180.0),
        "j6": (-360.0, 360.0),
    },
    "Lite 6 (6-DOF)": {
        "j1": (-360.0, 360.0),
        "j2": (-150.0, 150.0),
        "j3": (-3.5, 300.0),
        "j4": (-360.0, 360.0),
        "j5": (-124.0, 124.0),
        "j6": (-360.0, 360.0),
    },
    "Gen3 Lite (6-DOF)": {
        "j1": (-154.1, 154.1),
        "j2": (-154.1, 135.2),
        "j3": (-154.1, 154.1),
        "j4": (-148.4, 148.4),
        "j5": (-147.2, 147.2),
        "j6": (-148.4, 148.4),
    },
    "Gen2 (6-DOF)": {
        "j1": (-180.0, 180.0),
        "j2": (-180.0, 180.0),
        "j3": (-180.0, 180.0),
        "j4": (-180.0, 180.0),
        "j5": (-180.0, 180.0),
        "j6": (-180.0, 180.0),
    },
    "PiPER (6-DOF)": {
        "j1": (-150.0, 150.0),
        "j2": (0.0, 180.0),
        "j3": (-170.0, 0.0),
        "j4": (-100.0, 100.0),
        "j5": (-70.0, 70.0),
        "j6": (-120.0, 120.0),
    },
}


def joint_range_deg(model: str | None, joint: str) -> tuple[float, float]:
    """The (minimum, maximum) of one joint of a model, in degrees."""
    return JOINT_LIMITS_DEG.get(model or "", {}).get(joint, GENERIC_RANGE_DEG)


def clamp_joint(model: str | None, joint: str, value: float) -> float:
    low, high = joint_range_deg(model, joint)
    return min(high, max(low, value))
