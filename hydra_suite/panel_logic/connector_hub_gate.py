# =============================================================================
# HYDRA-UMC SUITE - panel_logic/connector_hub_gate.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The one switch of the connector hub's decision gate that this app edits: whether a caller on the hub's own machine is answered
# without a signed token (allowLoopbackNoIdentity, OFF by default). It goes through the server (GET and POST
# /api/connector-hub/gate/settings), which carries the administrator's own token to the hub; the hub keeps the switch, writes it to
# its settings file and records who changed it. Read without any window toolkit; a server without the route (404) or without the
# gate configured (503, available false) is told apart from an account that may not use it (401/403).
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _


def parse_settings(body: object) -> dict | None:
    """The settings in an answer of the route; None when the answer does not hold the switch as a boolean."""
    if not isinstance(body, dict) or not isinstance(body.get("allowLoopbackNoIdentity"), bool):
        return None
    return {
        "allow": body["allowLoopbackNoIdentity"],
        "loopbackAllowed": body.get("loopbackSwitchAllowed") is True,
        "verifiesTokens": body.get("verifiesTokens") is True,
        "persisted": body.get("persisted") is True,
    }


def body_for(allow: bool) -> dict:
    """The body of the change. Turning the switch on carries confirm: true; turning it off never does."""
    return {"allowLoopbackNoIdentity": True, "confirm": True} if allow else {"allowLoopbackNoIdentity": False}


def needs_confirmation(current: bool, wanted: bool) -> bool:
    return bool(wanted and not current)


def change_allowed(settings: dict, wanted: bool) -> bool:
    """Whether the hub would accept the change in the state it reported (it refuses the others as well)."""
    if wanted == settings["allow"]:
        return True
    return settings["loopbackAllowed"] if wanted else settings["verifiesTokens"]


def hidden_for(result: tuple[int, object] | None) -> bool:
    """True when the server has no such gate (no route, or the gate is not configured): the section stays out of the way."""
    if result is None:
        return False
    status, body = result
    return status == 404 or (status == 503 and isinstance(body, dict) and body.get("available") is False)


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading or change, empty when it worked."""
    if result is None:
        return _("HUBGATE_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("HUBGATE_FORBIDDEN")
    if status == 200 and parse_settings(body) is not None:
        return ""
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if status >= 300 and detail:
        return _("HUBGATE_SAVE_ERROR", reason=detail[:300])
    return _("HUBGATE_LOAD_ERROR")


def view(settings: dict | None) -> dict:
    """What the screen shows."""
    if settings is None:
        return {"available": False}
    return {
        "available": True,
        "allow": settings["allow"],
        "state": _("HUBGATE_STATE_ON") if settings["allow"] else _("HUBGATE_STATE_OFF"),
        "kept": _("HUBGATE_KEPT_FILE") if settings["persisted"] else _("HUBGATE_KEPT_MEMORY"),
        "canTurnOn": settings["loopbackAllowed"],
        "canTurnOff": settings["verifiesTokens"],
        "blockedOn": _("HUBGATE_LOOPBACK_ONLY"),
        "blockedOff": _("HUBGATE_NEEDS_KEY"),
    }
