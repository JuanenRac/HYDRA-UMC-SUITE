# =============================================================================
# HYDRA-UMC SUITE - panel_logic/viewport.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the viewport panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

from hydra_suite.render.kinematics import ROBOT_REGISTRY


SUPPORTED_MODELS = set(ROBOT_REGISTRY.keys())
