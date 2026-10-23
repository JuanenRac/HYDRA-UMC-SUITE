# =============================================================================
# HYDRA-UMC SUITE - panel_logic/tester.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the tester panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

# Matches Tester.tsx's own TOOL_CATEGORY exactly - lives here, not in
# can_ota.py, since STUDIO itself keeps this Tester-only.
_TOOL_CATEGORY: dict[str, str] = {
    "Soldering Station (T12)": "thermal",
    "3D Printing Hotend": "thermal",
    "Hot Air Rework Nozzle": "thermal",
    "Drill (BL4260)": "motor",
    "Smart Electric Screwdriver": "motor",
    "SMT Solder Paste Dispenser": "motor",
    "Thermal Paste / Liquid Dispenser": "motor",
    "Vacuum / Pneumatic Gripper": "vacuum",
    "Large-Format Vacuum Gripper": "vacuum",
    "Heavy-Duty Electromagnet": "binary",
    "Spot Welder Head": "binary",
    "Ultrasonic Welder / Packaging Sealer": "binary",
    "UV Curing Head": "binary",
}


def _category_for(tool: str) -> str:
    return _TOOL_CATEGORY.get(tool, "generic")
