# =============================================================================
# HYDRA-UMC SUITE - panel_logic/droid_estop.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The switch of the safety zones service that makes it read the emergency stop of the droids (droidEstop.enabled, OFF by default): a cut droid, a lost
# link or a silent bridge then keeps new starts from beginning in the cell, and never stops a machine that is running. It goes through the server (GET
# and POST /api/droid-estop/settings), which carries the administrator's own token to the service; the service keeps the switch, checks who asked and may
# refuse (no state file, the broker link cannot start). A change in either direction carries confirm: true. Read without any window toolkit; a server
# without the route (404) or without the service configured (503, available false) is told apart from an account that may not use it (401/403).
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _


def parse_settings(body: object) -> dict | None:
    """The settings in an answer of the route; None when the answer does not hold the switch as a boolean."""
    if not isinstance(body, dict) or not isinstance(body.get("enabled"), bool):
        return None
    return {"enabled": body["enabled"], "running": body.get("running") is True}


def body_for(enabled: bool) -> dict:
    """The body of the change: both directions carry the confirmation."""
    return {"enabled": bool(enabled), "confirm": True}


def needs_confirmation(current: bool, wanted: bool) -> bool:
    return current != wanted


def hidden_for(result: tuple[int, object] | None) -> bool:
    """True when the server has no such service (no route, or the service is not configured): the section stays out of the way."""
    if result is None:
        return False
    status, body = result
    return status == 404 or (status == 503 and isinstance(body, dict) and body.get("available") is False)


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading or change, empty when it worked."""
    if result is None:
        return _("DROIDESTOP_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("DROIDESTOP_FORBIDDEN")
    if status == 200 and parse_settings(body) is not None:
        return ""
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if status >= 300 and detail:
        return _("DROIDESTOP_SAVE_ERROR", reason=detail[:300])
    return _("DROIDESTOP_LOAD_ERROR")


def view(settings: dict | None) -> dict:
    """What the screen shows; every key is present even without the service, so the screen never binds to an undefined text."""
    if settings is None:
        return {"available": False, "enabled": False, "state": "", "link": ""}
    link = (_("DROIDESTOP_RUNNING") if settings["running"] else _("DROIDESTOP_NOT_RUNNING")) if settings["enabled"] else ""
    return {"available": True, "enabled": settings["enabled"], "state": _("DROIDESTOP_STATE_ON") if settings["enabled"] else _("DROIDESTOP_STATE_OFF"), "link": link}
