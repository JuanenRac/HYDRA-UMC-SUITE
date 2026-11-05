# =============================================================================
# HYDRA-UMC SUITE - panel_logic/hil_bridge.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The one switch of the HIL bridge that this app edits: whether a real command needs a pass verdict of the twin for its trajectory
# (require_twin_pass, OFF by default). It goes through the server (GET and POST /api/hil-bridge/settings), which carries the administrator's
# own token to the bridge; the bridge keeps the switch, checks who asked and may refuse (locked on, no twin key or robot, no file to keep it).
# A change in either direction carries confirm: true. Read without any window toolkit; a server without the route (404) or without the bridge
# configured (503, available false) is told apart from an account that may not use it (401/403).
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _


def parse_settings(body: object) -> dict | None:
    """The settings in an answer of the route; None when the answer does not hold the switch as a boolean."""
    if not isinstance(body, dict) or not isinstance(body.get("requireTwinPass"), bool):
        return None
    return {
        "require": body["requireTwinPass"],
        "locked": body.get("locked") is True,
        "persisted": body.get("persisted") is True,
        "ready": body.get("ready") is True,
        "canChange": body.get("canChange") is True,
    }


def body_for(require: bool) -> dict:
    """The body of the change: both directions carry the confirmation."""
    return {"requireTwinPass": bool(require), "confirm": True}


def needs_confirmation(current: bool, wanted: bool) -> bool:
    return current != wanted


def blocked_reason(settings: dict, wanted: bool) -> str:
    """Why the bridge would refuse the change in the state it reported ('' when it would accept it)."""
    if wanted == settings["require"]:
        return ""
    if not settings["canChange"]:
        return "no_identity"
    if not wanted and settings["locked"]:
        return "locked"
    if wanted and not settings["ready"]:
        return "not_ready"
    return ""


def hidden_for(result: tuple[int, object] | None) -> bool:
    """True when the server has no such bridge (no route, or the bridge is not configured): the section stays out of the way."""
    if result is None:
        return False
    status, body = result
    return status == 404 or (status == 503 and isinstance(body, dict) and body.get("available") is False)


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading or change, empty when it worked."""
    if result is None:
        return _("HILBRIDGE_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("HILBRIDGE_FORBIDDEN")
    if status == 200 and parse_settings(body) is not None:
        return ""
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if status >= 300 and detail:
        return _("HILBRIDGE_SAVE_ERROR", reason=detail[:300])
    return _("HILBRIDGE_LOAD_ERROR")


def view(settings: dict | None) -> dict:
    """What the screen shows; every key is present even without the bridge, so the screen never binds to an undefined text."""
    if settings is None:
        return {"available": False, "require": False, "state": "", "kept": "", "locked": "", "canChange": False}
    return {
        "available": True,
        "require": settings["require"],
        "state": _("HILBRIDGE_STATE_ON") if settings["require"] else _("HILBRIDGE_STATE_OFF"),
        "kept": _("HILBRIDGE_KEPT_FILE") if settings["persisted"] else _("HILBRIDGE_KEPT_MEMORY"),
        "locked": _("HILBRIDGE_LOCKED") if settings["locked"] else "",
        "canChange": True,
    }
