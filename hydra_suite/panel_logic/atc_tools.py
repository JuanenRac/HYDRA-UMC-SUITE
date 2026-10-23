# =============================================================================
# HYDRA-UMC SUITE - panel_logic/atc_tools.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the atc tools panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

from typing import Any


# STUDIO's own URTC_TOOLS (ATCToolsConfig.tsx) - deliberately NOT run
# through _() translation here either: STUDIO's own source never wraps
# these in t(), they're real tool-catalog names shown identically in
# every UI language on that side too, not an oversight to "fix" here.
URTC_TOOLS: tuple[str, ...] = (
    "None",
    "Soldering Station (T12)",
    "SMT Solder Paste Dispenser",
    "Thermal Paste / Liquid Dispenser",
    "Smart Electric Screwdriver",
    "Vacuum / Pneumatic Gripper",
    "Drill (BL4260)",
    "Gimbal Gripper",
    "NEMA Gripper",
    "AOI (Automated Optical Inspection) System",
    "Engraving Laser Diode (10W optical)",
    "3D Printing Hotend",
    "3D Scanner Probe",
    "SMT Pick & Place Head",
    "Heavy-Duty Electromagnet",
    "Spot Welder Head",
    "Conformal Coating Airbrush",
    "Large-Format Vacuum Gripper",
    "Functional Testing Head",
    "UV Curing Head",
    "Hot Air Rework Nozzle",
    "Pneumatic Press-Fit Inserter",
    "Wire Harnessing / Crimping Actuator",
    "PCB Advanced Inspection",
    "Solder Paste Jetting Valve",
    "Ultrasonic Welder / Packaging Sealer",
)


PANEL_GRIDS: tuple[str, ...] = ("1x1", "1x2", "2x1", "2x2", "2x3", "3x2", "3x3", "3x4", "4x3", "4x4")


JOINT_FIELDS: tuple[str, ...] = ("j1", "j2", "j3", "j4", "j5", "j6")


TABLE_FIELDS: tuple[str, ...] = ("tx", "ty")


JOINT_RANGE_DEG = (-180.0, 180.0)


TABLE_RANGE_MM = (-2000.0, 2000.0)


def _default_pos() -> dict[str, float]:
    return {f: 0.0 for f in JOINT_FIELDS + TABLE_FIELDS}


def _default_atc_config() -> dict[str, Any]:
    return {
        "type": "vertical_panel",
        "panelGrid": "2x2",
        "revolverSlots": 8,
        "tools": [],
    }
