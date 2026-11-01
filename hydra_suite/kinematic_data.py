# =============================================================================
# HYDRA-UMC SUITE - kinematic_data.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The range of each joint and the home pose of each robot model, read from assets/kinematic_data.json: the one file
# HYDRA-UMC-STUDIO and this program share (STUDIO keeps the same file as src/data/kinematicData.json). Before, each
# program had its own table typed by hand and they could drift apart. A model that is not in the file uses the
# generic range of -180 to 180 and the home pose of its own kinematics.
# =============================================================================
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

GENERIC_RANGE_DEG: tuple[float, float] = (-180.0, 180.0)
JOINTS: tuple[str, ...] = ("j1", "j2", "j3", "j4", "j5", "j6")

DATA_PATH = Path(__file__).resolve().parent.parent / "assets" / "kinematic_data.json"


@lru_cache(maxsize=1)
def load(path: Path = DATA_PATH) -> dict:
    """The whole file; a missing or damaged file is an error, not an empty table (a robot with the wrong limits is worse than none)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("models"), dict):
        raise ValueError(f"{path} is not a table of kinematic data")
    return data


def joint_limits(data: dict | None = None) -> dict[str, dict[str, tuple[float, float]]]:
    """{model: {joint: (minimum, maximum)}} in degrees."""
    models = (data or load())["models"]
    return {
        model: {joint: (float(pair[0]), float(pair[1])) for joint, pair in entry["limits"].items()}
        for model, entry in models.items()
    }


def home_poses(data: dict | None = None) -> dict[str, dict[str, float]]:
    """{model: {joint: degrees}} for the models that have a home pose in the file."""
    models = (data or load())["models"]
    return {model: {joint: float(value) for joint, value in entry.get("home", {}).items()} for model, entry in models.items() if entry.get("home")}
