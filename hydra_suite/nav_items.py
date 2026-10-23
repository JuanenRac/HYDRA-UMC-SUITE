# =============================================================================
# HYDRA-UMC SUITE - nav_items.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The navigation of the interface: a root menu plus three submenus (Industrial, URTC and HYDRA-UMC with its
# Ecosystem block), the same drill-down shape as HYDRA-UMC-STUDIO's sidebar. Each entry is a pair of the
# language key of its label and the key of the panel it opens. The interface and the checks both read this
# one list, so a panel cannot be added to one and forgotten in the other.
# =============================================================================
from __future__ import annotations

ROOT_ITEMS: tuple[tuple[str, str], ...] = (
    ("DOCK_SERVERS", "servers"),
    ("DOCK_OVERVIEW", "overview"),
    ("DOCK_VIEWPORT", "viewport"),
    ("DOCK_ROBOT_CONTROL", "robot"),
    ("DOCK_TRAJECTORY", "trajectory"),
    ("TAB_CAMERAS", "cameras"),
    ("TAB_CAMERA_MEDIA", "camera_media"),
    ("DOCK_LOGS", "logs"),
)

# (label key, panel key) pairs per submenu, matching the groupings of HYDRA-UMC-STUDIO's sidebar.
INDUSTRIAL_ITEMS: tuple[tuple[str, str], ...] = (
    ("DOCK_ROBOTS_CATALOG", "robots_catalog"),
    ("HEADING_XY_TABLE", "xy_table"),
    ("HEADING_ATC", "atc"),
    ("HEADING_RACK_MANAGER", "rack"),
    ("HEADING_PICK_AND_PLACE", "pick_and_place"),
    ("HEADING_CNC", "cnc"),
    ("HEADING_LASER", "laser"),
    ("HEADING_VACUUM_TABLE", "vacuum_table"),
    ("HEADING_HEATED_BED", "heated_bed"),
)

URTC_ITEMS: tuple[tuple[str, str], ...] = (
    ("NAV_FLASHER_STUDIO", "urtc_flasher"),
    ("NAV_TESTER_CENTER", "urtc_tester"),
)

HYDRAUMC_ITEMS: tuple[tuple[str, str], ...] = (
    ("NAV_FIRMWARE_UPDATE", "hydra_flasher"),
    ("NAV_HARDWARE_TESTER", "hydra_tester"),
    ("HEADING_KINEMATIC_BRAIN_STAGE", "kinematic_brain_stage"),
)

# The second block of the HYDRA-UMC submenu, under its own "Ecosystem" header: services, telemetry, the AI
# family and the administration screens. The administration screens answer with a refusal to an account that is
# not an administrator, and the safety limits screen says so instead of offering its controls.
HYDRAUMC_ECOSYSTEM_ITEMS: tuple[tuple[str, str], ...] = (
    ("DOCK_ECOSYSTEM_SERVICES", "ecosystem_services"),
    ("DOCK_ECOSYSTEM_TELEMETRY", "ecosystem_telemetry"),
    ("DOCK_AI_FAMILY", "ai_family"),
    ("DOCK_ADMIN_CLIENTS", "admin_clients"),
    ("DOCK_ADMIN_LOGS", "admin_logs"),
    ("DOCK_ADMIN_SERVER", "admin_server"),
    ("DOCK_SAFETY_LIMITS", "safety_limits"),
    ("DOCK_SYSTEM_SUPERVISOR", "system_supervisor"),
)

# Every panel key the navigation can reach.
ALL_DOCK_KEYS = frozenset(
    key
    for _label, key in (
        *ROOT_ITEMS, *INDUSTRIAL_ITEMS, *URTC_ITEMS, *HYDRAUMC_ITEMS, *HYDRAUMC_ECOSYSTEM_ITEMS,
    )
)
