# =============================================================================
# HYDRA-UMC SUITE - panel_logic/flasher.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the flasher panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

from hydra_suite.can_ota import CanOtaTier


# Matches HYDRA-UMC-STUDIO's own Dashboard.tsx exactly - two real, separate
# instance configurations, not one panel switching between tier sets.
URTC_TIERS: tuple[CanOtaTier, ...] = ("urtcHead", "urtcExpansion")


HYDRA_BRAIN_TIERS: tuple[CanOtaTier, ...] = ("kinematicBrain", "controllerBoard")


_TIER_LABEL_KEYS: dict[CanOtaTier, str] = {
    "kinematicBrain": "LBL_TARGET_KINEMATIC_BRAIN",
    "controllerBoard": "LBL_TARGET_CONTROLLER_BOARD",
    "urtcHead": "LBL_TARGET_URTC_HEAD",
    "urtcExpansion": "LBL_TARGET_URTC_EXPANSION",
}
