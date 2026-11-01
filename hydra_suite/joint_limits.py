# =============================================================================
# HYDRA-UMC SUITE - joint_limits.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The range of every joint of the models that have a published one, in degrees, the same table HYDRA-UMC-STUDIO
# uses to clamp its own jog (so a slider can never ask a joint for more than the robot can turn). A model without an
# entry gets the generic -180..180 range. The table is not written here: it is assets/kinematic_data.json, the one
# file both programs read (hydra_suite/kinematic_data.py), together with the home pose of each model.
# =============================================================================
from __future__ import annotations

from hydra_suite import kinematic_data

GENERIC_RANGE_DEG: tuple[float, float] = kinematic_data.GENERIC_RANGE_DEG

JOINT_LIMITS_DEG: dict[str, dict[str, tuple[float, float]]] = kinematic_data.joint_limits()


def joint_range_deg(model: str | None, joint: str) -> tuple[float, float]:
    """The (minimum, maximum) of one joint of a model, in degrees."""
    return JOINT_LIMITS_DEG.get(model or "", {}).get(joint, GENERIC_RANGE_DEG)


def clamp_joint(model: str | None, joint: str, value: float) -> float:
    low, high = joint_range_deg(model, joint)
    return min(high, max(low, value))
