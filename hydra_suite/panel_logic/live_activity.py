# =============================================================================
# HYDRA-UMC SUITE - panel_logic/live_activity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Live Activity of a robot on the lock screen of an iPhone (the push.liveActivity block of GET/PUT /api/admin/server-config), OFF by default. The level is what
# the card may show: only the state of the robot (the default), the state and the progress, or everything of the panel; "full" is the most there is and the server
# applies the level before anything leaves it. Turning the card on or choosing a level above the saved one shows more to whoever holds the phone, so the request
# carries confirm: true then; turning it off or lowering the level never does. Read without any window toolkit; a missing block means a server that predates it.
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _

LEVELS = ("status", "progress", "full")
SOURCES = ("env", "config", "default")


def _rank(level: str) -> int:
    return LEVELS.index(level)


def parse_state(body: object) -> dict | None:
    """The block in the answer of the server configuration; None when it is missing or damaged."""
    if not isinstance(body, dict):
        return None
    push = body.get("push")
    live = push.get("liveActivity") if isinstance(push, dict) else None
    if not isinstance(live, dict):
        return None
    enabled, level = live.get("enabled"), live.get("level")
    if not isinstance(enabled, dict) or type(enabled.get("value")) is not bool or enabled.get("source") not in SOURCES:
        return None
    if not isinstance(level, dict) or level.get("value") not in LEVELS or level.get("source") not in SOURCES:
        return None
    maximum = live.get("maxLevel") if live.get("maxLevel") in LEVELS else "full"
    push_enabled = push.get("enabled") if isinstance(push, dict) else None
    return {
        "enabled": enabled["value"], "enabled_locked": enabled["source"] == "env",
        "level": level["value"], "level_locked": level["source"] == "env",
        "max_level": maximum,
        "push_on": isinstance(push_enabled, dict) and push_enabled.get("value") is True,
    }


def allowed_levels(state: dict) -> list[str]:
    """The levels a person may pick: none above the most the server allows."""
    return [level for level in LEVELS if _rank(level) <= _rank(state["max_level"])]


def change_for(state: dict, wanted_enabled: bool, wanted_level: str) -> dict:
    """What differs from the saved state, never touching a value that the environment fixes and never a level above the maximum."""
    change: dict = {}
    if not state["enabled_locked"] and wanted_enabled != state["enabled"]:
        change["enabled"] = wanted_enabled
    if not state["level_locked"] and wanted_level in LEVELS and wanted_level != state["level"] and _rank(wanted_level) <= _rank(state["max_level"]):
        change["level"] = wanted_level
    return change


def needs_confirmation(state: dict, change: dict) -> bool:
    """Turning the card on, or a level above the saved one, is what shows more on a lock screen."""
    if change.get("enabled") is True and not state["enabled"]:
        return True
    return "level" in change and _rank(change["level"]) > _rank(state["level"])


def body_for(state: dict, change: dict) -> dict:
    """The body of the change: only what changes, and confirm: true exactly when it is needed."""
    live: dict = {}
    if "enabled" in change:
        live["enabled"] = change["enabled"]
    if "level" in change:
        live["level"] = change["level"]
    if needs_confirmation(state, change):
        live["confirm"] = True
    return {"push": {"liveActivity": live}}


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed change, empty when it worked."""
    if result is None:
        return _("LIVEACT_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("LIVEACT_FORBIDDEN")
    if status == 200:
        return ""
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if detail:
        return _("LIVEACT_SAVE_ERROR", reason=detail[:300])
    return _("LIVEACT_LOAD_ERROR")


def view(state: dict | None, wanted_enabled: bool | None = None, wanted_level: str | None = None) -> dict:
    """What the screen shows; every key is always there so the screen can bind to it."""
    if state is None:
        return {"available": False, "enabled": False, "level": "status", "locked": False, "lockedText": "", "pushOffText": "", "levels": [], "dirty": False}
    enabled = state["enabled"] if wanted_enabled is None else wanted_enabled
    level = state["level"] if wanted_level not in LEVELS else wanted_level
    locked = state["enabled_locked"] or state["level_locked"]
    return {
        "available": True, "enabled": enabled, "level": level, "locked": locked, "lockedText": _("LIVEACT_LOCKED") if locked else "",
        "pushOffText": "" if state["push_on"] else _("LIVEACT_PUSH_OFF"),
        "levels": [{"id": item, "label": _("LIVEACT_LEVEL_" + item.upper()), "hint": _("LIVEACT_LEVEL_" + item.upper() + "_HINT"), "selected": item == level} for item in allowed_levels(state)],
        "dirty": bool(change_for(state, enabled, level)),
    }
