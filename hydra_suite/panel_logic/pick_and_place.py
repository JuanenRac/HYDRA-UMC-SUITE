# =============================================================================
# HYDRA-UMC SUITE - panel_logic/pick_and_place.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the pick and place panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

MACHINE_TYPES: tuple[str, ...] = ("juanenPnP", "lumenPnP")


MACHINE_LABELS: dict[str, str] = {"juanenPnP": "JuanenPnP", "lumenPnP": "LumenPnP"}


# (field, label key, min, max) - real fixed hardware bounds, matching
# PickAndPlace.tsx's own literal values exactly.
PNP_AXES: tuple[tuple[str, str, int, int], ...] = (
    ("axisX", "LBL_PNP_AXIS_X", 0, 433),
    ("axisY", "LBL_PNP_AXIS_Y", 0, 487),
    ("axisZ", "LBL_PNP_AXIS_Z", 0, 90),
    ("nozzle1Rotation", "LBL_PNP_NOZZLE1", -180, 180),
    ("nozzle2Rotation", "LBL_PNP_NOZZLE2", -180, 180),
)
