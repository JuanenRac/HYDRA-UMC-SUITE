# =============================================================================
# HYDRA-UMC SUITE - panel_logic/detection_hef.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The switch of the loaded-model reports of the DETECTION-HEF service (the detectionHef block of GET/PUT /api/admin/server-config), OFF by
# default. The server writes a settings file that the service re-reads while it runs; this app only changes the switch. Turning it on carries
# confirm: true; turning it off never does. Read without any window toolkit; a block missing from the answer means a server that predates it.
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _

SOURCES = ("env", "config", "default")


def parse_state(body: object) -> dict | None:
    """The switch in the answer of the server configuration; None when the block is missing or damaged."""
    if not isinstance(body, dict):
        return None
    block = body.get("detectionHef")
    item = block.get("acceptLoadedReports") if isinstance(block, dict) else None
    if not isinstance(item, dict) or type(item.get("value")) is not bool or item.get("source") not in SOURCES:
        return None
    return {"enabled": item["value"], "locked": item["source"] == "env"}


def body_for(enabled: bool) -> dict:
    """The body of the change. Turning the switch on carries confirm: true; turning it off never does."""
    return {"detectionHef": {"acceptLoadedReports": True, "confirm": True} if enabled else {"acceptLoadedReports": False}}


def needs_confirmation(current: bool, wanted: bool) -> bool:
    return bool(wanted and not current)


def change_allowed(state: dict, wanted: bool) -> bool:
    """The environment of the server can lock the switch; then no change is offered."""
    return wanted == state["enabled"] or not state["locked"]


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed change, empty when it worked."""
    if result is None:
        return _("DETHEF_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("DETHEF_FORBIDDEN")
    if status == 200:
        return ""
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if detail:
        return _("DETHEF_SAVE_ERROR", reason=detail[:300])
    return _("DETHEF_LOAD_ERROR")


def view(state: dict | None) -> dict:
    """What the screen shows; every key is always there so the screen can bind to it."""
    if state is None:
        return {"available": False, "enabled": False, "locked": False, "lockedText": ""}
    return {"available": True, "enabled": state["enabled"], "locked": state["locked"], "lockedText": _("DETHEF_LOCKED") if state["locked"] else ""}
