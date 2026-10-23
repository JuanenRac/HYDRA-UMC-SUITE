# =============================================================================
# HYDRA-UMC SUITE - panel_logic/xy_table.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the xy table panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

# Matches XYTableConfig.tsx's own `xyTable?.tableSize.width || 500` -
# what shows in the size fields before any real xyTable object exists.
_DISPLAY_DEFAULT_SIZE_MM = 500


# Matches XYTableConfig.tsx's own handleReset() - what Reset actually
# writes. Deliberately different from the display default above - see
# this file's own header.
_RESET_SIZE_MM = 300


JOG_STEPS_MM: tuple[float, ...] = (0.01, 0.1, 1.0, 2.0, 5.0, 10.0, 100.0)


def _default_xy_table() -> dict:
    return {
        "pos": {"x": 0, "y": 0},
        "tableSize": {"width": _RESET_SIZE_MM, "length": _RESET_SIZE_MM},
        "worldPos": {"x": 0, "y": 0},
        "worldRot": 0,
        "renderScale": 1,
    }
