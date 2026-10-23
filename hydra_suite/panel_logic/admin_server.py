# =============================================================================
# HYDRA-UMC SUITE - panel_logic/admin_server.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the admin server panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

def _format_uptime(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"
