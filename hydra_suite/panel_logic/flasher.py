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


PROGRESS_PHASES = ("connecting", "entering_bootloader", "erasing_fram", "transferring", "verifying", "rebooting", "done", "error")


def progress_line(payload: object) -> dict | None:
    """What one `canota_progress` line of a real flash cycle shows: the phase, the percent (0 to 100), the page counts and, for an error, the reason the
    bootloader client reports. None when the line is not one (no phase this window knows). During the transfer only every fifth page and the last one
    are worth a line of the log, as in HYDRA-UMC STUDIO."""
    if not isinstance(payload, dict) or payload.get("phase") not in PROGRESS_PHASES:
        return None
    percent = payload.get("percent")
    percent = max(0, min(100, round(percent))) if isinstance(percent, (int, float)) and not isinstance(percent, bool) else None
    sent, total = payload.get("pages_sent"), payload.get("pages_total")
    pages = (sent, total) if all(type(n) is int and n >= 0 for n in (sent, total)) else None
    reason = payload.get("error") if isinstance(payload.get("error"), str) else None
    phase = payload["phase"]
    log = not (phase == "transferring" and pages is not None and pages[0] % 5 != 0 and pages[0] != pages[1])
    return {"phase": phase, "percent": percent, "pages": pages, "reason": reason, "log": log}


_TIER_LABEL_KEYS: dict[CanOtaTier, str] = {
    "kinematicBrain": "LBL_TARGET_KINEMATIC_BRAIN",
    "controllerBoard": "LBL_TARGET_CONTROLLER_BOARD",
    "urtcHead": "LBL_TARGET_URTC_HEAD",
    "urtcExpansion": "LBL_TARGET_URTC_EXPANSION",
}
