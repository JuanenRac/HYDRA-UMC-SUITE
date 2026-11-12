# =============================================================================
# HYDRA-UMC SUITE - panel_logic/stop_state.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The one stop state of the installation (the same badge as in HYDRA-UMC STUDIO): the server pushes a `stop-state` message on the socket, right after the
# connection opens and at every change, that joins the physical emergency stop (the frame on identifier 0x001, as the kinematic brain holds it) with the global stop.
# `unknown` for the physical part means that the server does not watch it (its default) or could not read it, and it is never shown as released. This file is the
# part without any window toolkit: how a message is read, how the state of several servers is summed up and the lines of the badge. It only reads: nothing here
# sends a stop.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

from hydra_suite.i18n import _

STATES = ("STOPPED", "READY", "UNKNOWN")
PHYSICALS = ("latched", "ready", "unknown")
SOFTWARES = ("stopped", "ready")

SEVERITY_ERROR = "error"
SEVERITY_OK = "ok"
SEVERITY_MUTED = "muted"


@dataclass(frozen=True)
class StopStateView:
    state: str
    physical: str
    software: str
    physical_link_ok: bool | None = None
    changed_at: int = 0


def parse_stop_state(message: object) -> StopStateView | None:
    """The state of a `stop-state` message, or None for anything that is not a complete one: a damaged message is ignored, never half-applied."""
    if not isinstance(message, dict) or message.get("type") != "stop-state":
        return None
    body = message.get("state")
    if not isinstance(body, dict):
        return None
    state, physical, software = body.get("state"), body.get("physical"), body.get("software")
    if state not in STATES or physical not in PHYSICALS or software not in SOFTWARES:
        return None
    link = body.get("physicalLinkOk")
    changed = body.get("changedAt")
    return StopStateView(
        state=state,
        physical=physical,
        software=software,
        physical_link_ok=link if isinstance(link, bool) else None,
        changed_at=changed if isinstance(changed, int) and not isinstance(changed, bool) else 0,
    )


def sum_up(views: list[StopStateView]) -> StopStateView | None:
    """The state of several servers as one: STOPPED if any is stopped, UNKNOWN if any is unknown, READY only if every one that spoke is ready; None when none spoke."""
    if not views:
        return None
    for wanted in ("STOPPED", "UNKNOWN"):
        for view in views:
            if view.state == wanted:
                return view
    return views[0]


def severity(view: StopStateView | None) -> str:
    if view is None:
        return ""
    return {"STOPPED": SEVERITY_ERROR, "READY": SEVERITY_OK}.get(view.state, SEVERITY_MUTED)


def badge_text(view: StopStateView | None) -> str:
    """The word of the badge, in the language of the person; empty before any server has said anything (nothing is drawn)."""
    if view is None:
        return ""
    return _({"STOPPED": "STOP_STATE_STOPPED", "READY": "STOP_STATE_READY"}.get(view.state, "STOP_STATE_UNKNOWN"))


def badge_tooltip(view: StopStateView | None) -> str:
    if view is None:
        return ""
    physical = _({"latched": "STOP_STATE_PHYSICAL_LATCHED", "ready": "STOP_STATE_PHYSICAL_READY"}.get(view.physical, "STOP_STATE_PHYSICAL_UNKNOWN"))
    software = _("STOP_STATE_SOFTWARE_STOPPED" if view.software == "stopped" else "STOP_STATE_SOFTWARE_READY")
    return _("STOP_STATE_TOOLTIP", physical=physical, software=software)
