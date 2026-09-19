# =============================================================================
# HYDRA-UMC SUITE - robot_catalog.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Manufacturer/DOF metadata for every real robot model this ecosystem has
# kinematics/mesh support for - the exact same 24-model set and
# manufacturer labels as HYDRA-UMC-STUDIO's own store.tsx
# ROBOT_MANUFACTURERS (keep both in sync by hand; there is no shared
# source file across the TypeScript/Python boundary for this ecosystem).
# Used by the Robots catalog panel; render/kinematics.py's own
# ROBOT_REGISTRY is the one source of truth for the model NAME strings
# themselves (this module's own keys are asserted to match it exactly,
# see tests/verify_robots_catalog_panel.py).
# =============================================================================
from __future__ import annotations

import re

ROBOT_MANUFACTURERS: dict[str, str] = {
    "Parol6 (6-DOF)": "Source Robotics",
    "Faze4 (6-DOF)": "Source Robotics",
    "AR3 (6-DOF)": "Annin Robotics",
    "AR4 (6-DOF)": "Annin Robotics",
    "UR3e (6-DOF)": "Universal Robots",
    "UR5e (6-DOF)": "Universal Robots",
    "UR10e (6-DOF)": "Universal Robots",
    "UR16e (6-DOF)": "Universal Robots",
    "UR20 (6-DOF)": "Universal Robots",
    "xArm6 (6-DOF)": "UFACTORY",
    "Lite 6 (6-DOF)": "UFACTORY",
    "e.DO (6-DOF)": "Comau",
    "Gen3 Lite (6-DOF)": "Kinova",
    "M-710iC (6-DOF)": "FANUC",
    "SO-ARM100 (5-DOF)": "The Robot Studio",
    "Gen2 (6-DOF)": "Kinova",
    "PiPER (6-DOF)": "AgileX",
    "Z1 (6-DOF)": "Unitree",
    "ViperX 300 (6-DOF)": "Trossen Robotics",
    "WidowX 250 (6-DOF)": "Trossen Robotics",
    "Koch v1.1 (5-DOF)": "Koch / Low-Cost Robot Arm",
    "UR3 (6-DOF)": "Universal Robots (classic)",
    "UR5 (6-DOF)": "Universal Robots (classic)",
    "UR10 (6-DOF)": "Universal Robots (classic)",
}

REAL_ROBOT_MODELS: list[str] = list(ROBOT_MANUFACTURERS.keys())

_DOF_PATTERN = re.compile(r"\((\d+)-DOF\)")


def robot_model_dof(model: str) -> int:
    match = _DOF_PATTERN.search(model)
    return int(match.group(1)) if match else 6
