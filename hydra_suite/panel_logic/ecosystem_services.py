# =============================================================================
# HYDRA-UMC SUITE - panel_logic/ecosystem_services.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The values and helpers of the ecosystem services panel that do not depend on any window toolkit: the Qt Quick
# interface and the checks use them directly.
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _


_STACK_COLOR = {
    "python": "#e0c040",
    "node": "#4caf50",
    "rust": "#e08030",
    "go": "#4fc3f7",
    "android": "#4caf50",
    "flutter": "#38bdf8",
    "firmware-c": "#c060e0",
}


# Same 4 health colors STUDIO's own healthColor() computes, from the same
# real signals (a port probe's own `live`, a systemd probe's own
# `activeState`) - see EcosystemServices.tsx's own header comment for the
# full reasoning behind each branch, unchanged here.
_HEALTH_COLOR = {
    "green": "#4caf50",
    "red": "#e05050",
    "amber": "#e0a030",
    "slate": "#556070",
}


def _health(project: dict) -> str:
    active_state = project.get("activeState")
    live = project.get("live")
    if active_state == "failed":
        return "amber"
    if active_state == "active":
        return "amber" if live is False else "green"
    if active_state:
        return "red"  # inactive/deactivating/activating under systemd control, not active
    if live is True:
        return "green"
    if live is False:
        return "red"
    return "slate"


def _badge_label(project: dict) -> str:
    active_state = project.get("activeState")
    live = project.get("live")
    if active_state == "failed" or (active_state == "active" and live is False):
        return _("LBL_SERVICES_ERROR")
    if live is True:
        return _("LBL_SERVICES_LIVE")
    if live is False:
        return _("LBL_SERVICES_DEAD")
    if active_state == "active":
        return _("LBL_SERVICES_RUNNING")
    if active_state:
        return _("LBL_SERVICES_STOPPED")
    return _("LBL_SERVICES_NOT_A_SERVICE")
