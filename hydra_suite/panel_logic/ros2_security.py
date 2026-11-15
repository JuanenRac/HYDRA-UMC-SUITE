# =============================================================================
# HYDRA-UMC SUITE - panel_logic/ros2_security.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The requirement of ROS 2 security (SROS2) of the ROS 2 bridge (security.require_sros2, OFF by default, so a machine without a keystore keeps
# starting). The bridge keeps it in its own configuration file and applies a change only when it restarts. It goes through the server (GET and POST
# /api/ros2-bridge/settings), which carries the administrator's own token to the bridge; the bridge checks who asked and may refuse (started without
# allowing the change). A change in either direction carries confirm: true. When the server has no connection to the bridge the screen falls back to
# preparing the lines to add to the file of the bridge by hand (nothing is sent), and it never says that the bridge is secured. Read without any
# window toolkit.
# =============================================================================
from __future__ import annotations

import json

from hydra_suite.i18n import _

# What the bridge checks in its environment when the requirement is on (ROS 2 itself reads these variables).
ENVIRONMENT = (
    "ROS_SECURITY_ENABLE=true",
    "ROS_SECURITY_STRATEGY=Enforce",
    'ROS_SECURITY_KEYSTORE=<directory that holds "enclaves">',
)


def preparation(required: bool) -> dict | None:
    """The lines to add for the wanted value; None for the default (off), where there is nothing to add."""
    if not required:
        return None
    return {"config": json.dumps({"security": {"require_sros2": True}}, indent=2), "environment": list(ENVIRONMENT)}


def view(required: bool) -> dict:
    """The fallback section: the plain statement, the state sentence and, only when switched on, the lines to add by hand."""
    prepared = preparation(required)
    return {
        "notReported": _("ROS2SEC_NOT_REPORTED"),
        "state": _("ROS2SEC_STATE_ON") if prepared else _("ROS2SEC_STATE_OFF"),
        "prepared": prepared is not None,
        "config": prepared["config"] if prepared else "",
        "environment": "\n".join(prepared["environment"]) if prepared else "",
    }


def parse_settings(body: object) -> dict | None:
    """The settings in an answer of the route; None when the answer does not hold the requirement as a boolean."""
    if not isinstance(body, dict) or not isinstance(body.get("requireSros2"), bool):
        return None
    return {
        "require": body["requireSros2"],
        "active": body.get("active") is True,
        "restartNeeded": body.get("restartNeeded") is True,
        "canChange": body.get("canChange") is True,
        "environmentReady": body.get("environmentReady") is True,
    }


def body_for(require: bool) -> dict:
    """The body of the change: both directions carry the confirmation."""
    return {"requireSros2": bool(require), "confirm": True}


def needs_confirmation(current: bool, wanted: bool) -> bool:
    return current != wanted


def blocked_reason(settings: dict, wanted: bool) -> str:
    """Why the bridge would refuse the change in the state it reported ('' when it would accept it)."""
    if wanted == settings["require"]:
        return ""
    return "" if settings["canChange"] else "blocked_no_change"


def problem_for(result: tuple[int, object] | None) -> str:
    """The sentence for a reading or a change that did not work, empty when it worked (then the section shows the bridge)."""
    if result is None:
        return _("ROS2SEC_LOAD_ERROR")
    status, body = result
    if status == 404:
        return _("ROS2SEC_UNSUPPORTED")
    if status == 503:
        return _("ROS2SEC_NOT_CONFIGURED") if isinstance(body, dict) and body.get("available") is False else _("ROS2SEC_UNREACHABLE")
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if status in (401, 403):
        return _("ROS2SEC_SAVE_ERROR", reason=detail[:300]) if detail else _("ROS2SEC_FORBIDDEN")
    if status == 200 and parse_settings(body) is not None:
        return ""
    if status >= 300 and detail:
        return _("ROS2SEC_SAVE_ERROR", reason=detail[:300])
    return _("ROS2SEC_LOAD_ERROR")


def live_view(settings: dict | None) -> dict:
    """What the screen shows when the bridge answered; every key is present without it, so the screen never binds to an undefined text."""
    if settings is None:
        return {"live": False, "require": False, "state": "", "active": "", "restart": "", "environment": "", "environmentReady": False}
    return {
        "live": True,
        "require": settings["require"],
        "state": _("ROS2SEC_STATE_FILE_ON") if settings["require"] else _("ROS2SEC_STATE_FILE_OFF"),
        "active": _("ROS2SEC_ACTIVE_ON") if settings["active"] else _("ROS2SEC_ACTIVE_OFF"),
        "restart": _("ROS2SEC_RESTART_NEEDED") if settings["restartNeeded"] else "",
        "environment": _("ROS2SEC_ENV_READY") if settings["environmentReady"] else _("ROS2SEC_ENV_NOT_READY"),
        "environmentReady": settings["environmentReady"],
    }
