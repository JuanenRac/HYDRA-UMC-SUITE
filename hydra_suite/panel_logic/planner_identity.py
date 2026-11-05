# =============================================================================
# HYDRA-UMC SUITE - panel_logic/planner_identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The one switch of the semantic planner that this app edits: whether the approval of a plan needs the person who is signed in
# (plan_approval.require_identity, ON by default). It goes through the server (GET and POST /api/semantic-planner/settings), which carries
# the administrator's own token to the planner; the planner keeps the switch, writes it to its configuration file and prints who changed
# it. Read without any window toolkit; a server without the route (404) or without the planner configured (503, available false) is told
# apart from an account that may not use it (401/403).
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _


def parse_settings(body: object) -> dict | None:
    """The settings in an answer of the route; None when the answer does not hold the switch as a boolean."""
    if not isinstance(body, dict) or not isinstance(body.get("requireIdentity"), bool):
        return None
    return {
        "require": body["requireIdentity"],
        "verifiesTokens": body.get("verifiesTokens") is True,
        "persisted": body.get("persisted") is True,
    }


def body_for(require: bool) -> dict:
    """The body of the change. Relaxing the switch (False) carries confirm: true; tightening it never does."""
    return {"requireIdentity": True} if require else {"requireIdentity": False, "confirm": True}


def needs_confirmation(current: bool, wanted: bool) -> bool:
    return bool(current and not wanted)


def change_allowed(settings: dict, wanted: bool) -> bool:
    """Whether the planner would accept the change in the state it reported (without the identity key it refuses any change)."""
    return wanted == settings["require"] or settings["verifiesTokens"]


def hidden_for(result: tuple[int, object] | None) -> bool:
    """True when the server has no such planner (no route, or the planner is not configured): the section stays out of the way."""
    if result is None:
        return False
    status, body = result
    return status == 404 or (status == 503 and isinstance(body, dict) and body.get("available") is False)


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading or change, empty when it worked."""
    if result is None:
        return _("PLANNERID_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("PLANNERID_FORBIDDEN")
    if status == 200 and parse_settings(body) is not None:
        return ""
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if status >= 300 and detail:
        return _("PLANNERID_SAVE_ERROR", reason=detail[:300])
    return _("PLANNERID_LOAD_ERROR")


def view(settings: dict | None) -> dict:
    """What the screen shows."""
    if settings is None:
        # every key is present even without the planner, so the screen never binds to an undefined text
        return {"available": False, "require": True, "state": "", "kept": "", "canChange": False, "blocked": ""}
    return {
        "available": True,
        "require": settings["require"],
        "state": _("PLANNERID_STATE_ON") if settings["require"] else _("PLANNERID_STATE_OFF"),
        "kept": _("PLANNERID_KEPT_FILE") if settings["persisted"] else _("PLANNERID_KEPT_MEMORY"),
        "canChange": settings["verifiesTokens"],
        "blocked": _("PLANNERID_NEEDS_KEY"),
    }
