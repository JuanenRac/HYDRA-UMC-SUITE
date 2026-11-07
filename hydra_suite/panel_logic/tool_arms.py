# =============================================================================
# HYDRA-UMC SUITE - panel_logic/tool_arms.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The arm state of the URTC tools as the server relays it (GET /api/tool-arms, read only): for each pair of robot and tool whether its power
# stage may act, who reported it and how old the report is. A stale report is never shown as safe: a stale armed tool is a warning and a stale
# disarmed tool is unknown. Nothing here arms, disarms or stops anything. Read without any window toolkit; the answer is checked against the
# closed shape of the contract and one bad row refuses the whole answer, so a half-read list is never shown as the truth.
# =============================================================================
from __future__ import annotations

import math
import re

from hydra_suite.i18n import _

MAX_ARMS = 256
MAX_TOOL_ID = 24
_ROBOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:\-]{0,63}")
_RANK = {"warning": 0, "armed": 1, "unknown": 2, "disarmed": 3}


def _whole(value: object, low: int, high: int | None = None) -> bool:
    return type(value) is int and value >= low and (high is None or value <= high)


def _real(value: object, low: float, *, exclusive: bool = False) -> bool:
    if type(value) not in (int, float) or not math.isfinite(value):
        return False
    return value > low if exclusive else value >= low


def parse_report(body: object) -> dict | None:
    """The report in an answer of the route; None when anything does not have the shape of the contract."""
    if not isinstance(body, dict) or body.get("schema_version") != "1.0":
        return None
    if not _real(body.get("ttlSeconds"), 0, exclusive=True):
        return None
    arms_raw = body.get("arms")
    if not isinstance(arms_raw, list) or len(arms_raw) > MAX_ARMS:
        return None
    if not _whole(body.get("armedCount"), 0) or not _whole(body.get("staleCount"), 0):
        return None
    arms = []
    for item in arms_raw:
        if not isinstance(item, dict):
            return None
        robot, by = item.get("robot"), item.get("by")
        if not isinstance(robot, str) or not _ROBOT.fullmatch(robot) or not isinstance(by, str) or len(by) > 64:
            return None
        if not _whole(item.get("toolId"), 0, MAX_TOOL_ID) or not _whole(item.get("seq"), 1) or not _real(item.get("ageSeconds"), 0):
            return None
        if type(item.get("armed")) is not bool or type(item.get("stale")) is not bool:
            return None
        arms.append({"robot": robot, "toolId": item["toolId"], "armed": item["armed"], "by": by, "seq": item["seq"], "ageSeconds": float(item["ageSeconds"]), "stale": item["stale"]})
    return {"ttlSeconds": float(body["ttlSeconds"]), "arms": arms, "armedCount": body["armedCount"], "staleCount": body["staleCount"]}


def level_of(arm: dict) -> str:
    """A stale armed tool is a warning and a stale disarmed tool is unknown: a stale report is never shown as safe."""
    if arm["stale"]:
        return "warning" if arm["armed"] else "unknown"
    return "armed" if arm["armed"] else "disarmed"


def sorted_arms(arms: list[dict]) -> list[dict]:
    """The dangerous rows first (warning, armed), then unknown, then disarmed; then by robot and tool. The input is not changed."""
    return sorted(arms, key=lambda a: (_RANK[level_of(a)], a["robot"], a["toolId"]))


def age_parts(seconds: float) -> tuple[str, int]:
    """The age as (unit, value): seconds under a minute, minutes under an hour, otherwise hours."""
    if seconds < 60:
        return "s", int(seconds)
    if seconds < 3600:
        return "min", int(seconds // 60)
    return "h", int(seconds // 3600)


def hidden_for(result: tuple[int, object] | None) -> bool:
    """True when the server predates the route (404)."""
    return result is not None and result[0] == 404


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading, empty when it worked."""
    if result is None:
        return _("TOOLARMS_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("TOOLARMS_FORBIDDEN")
    # the server answers 502/503/504 while it has no address of the safety zones service or cannot reach it; that service answers 404 without --tool-arms
    if status in (404, 502, 503, 504):
        return _("TOOLARMS_UNAVAILABLE")
    if status == 200 and parse_report(body) is not None:
        return ""
    return _("TOOLARMS_LOAD_ERROR")


def _row(arm: dict) -> str:
    unit, value = age_parts(arm["ageSeconds"])
    parts = [arm["robot"], _("TOOLARMS_TOOL", id=arm["toolId"]), _("TOOLARMS_LEVEL_" + level_of(arm).upper()), _("TOOLARMS_AGE", value=value, unit=_("TOOLARMS_UNIT_" + unit.upper()))]
    if arm["by"]:
        parts.append(_("TOOLARMS_BY", by=arm["by"]))
    return "  |  ".join(parts)


def view(report: dict | None) -> dict:
    """What the screen shows; every key is always there so the screen can bind to it."""
    if report is None:
        return {"available": False, "summary": "", "rows": [], "empty": "", "staleNote": ""}
    rows = [{"text": _row(a), "level": level_of(a)} for a in sorted_arms(report["arms"])]
    return {
        "available": True,
        "summary": _("TOOLARMS_SUMMARY", armed=report["armedCount"], stale=report["staleCount"], ttl=f"{report['ttlSeconds']:g}"),
        "rows": rows,
        "empty": "" if rows else _("TOOLARMS_EMPTY"),
        "staleNote": _("TOOLARMS_STALE_NOTE"),
    }
