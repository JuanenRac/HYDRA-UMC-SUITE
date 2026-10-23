# =============================================================================
# HYDRA-UMC SUITE - panel_logic/kinematic_brain_stage.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the kinematic brain stage panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

from hydra_suite.models import default_kinematic_brain_stage


AXIS_KEYS: tuple[str, ...] = ("x", "y1", "y2", "z")


JOG_STEPS_MM: tuple[float, ...] = (0.01, 0.1, 1.0, 2.0, 5.0, 10.0, 100.0)


# (endstop key, label) - matches KinematicBrainStage.tsx's own endstopEntries exactly.
ENDSTOP_ENTRIES: tuple[tuple[str, str], ...] = (
    ("xMin", "X MIN"), ("xMax", "X MAX"),
    ("y1Min", "Y1 MIN"), ("y1Max", "Y1 MAX"),
    ("y2Min", "Y2 MIN"), ("y2Max", "Y2 MAX"),
    ("zMin", "Z MIN"), ("zMax", "Z MAX"),
    ("e0Min", "E0 MIN"), ("e0Max", "E0 MAX"),
    ("e1Min", "E1 MIN"), ("e1Max", "E1 MAX"),
)


def _fill_from(value, default):
    """`value` with every missing or wrongly typed entry taken from `default`
    (recursively); the lists keep their own length, only a non-list is replaced."""
    if isinstance(default, dict):
        source = value if isinstance(value, dict) else {}
        return {key: _fill_from(source.get(key), item) for key, item in default.items()} | {
            key: item for key, item in source.items() if key not in default
        }
    if isinstance(default, list):
        return value if isinstance(value, list) else list(default)
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, (int, float)):
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default
    return value if isinstance(value, type(default)) else default


def complete_stage(stage) -> dict:
    """A copy of the controller's stage where whatever the server left out or
    sent as another type reads as the seed default, so a half-filled record
    never stops the panel from drawing."""
    return _fill_from(stage, default_kinematic_brain_stage())


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
