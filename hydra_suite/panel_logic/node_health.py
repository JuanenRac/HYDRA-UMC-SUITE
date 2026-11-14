# =============================================================================
# HYDRA-UMC SUITE - hydra_suite/panel_logic/node_health.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The last health frame that the kinematic brain heard from each controller board (GET /api/ecosystem/node-health?slot=N of the server), read defensively.

Read only. A server that predates the route, or one where an administrator did not turn it on, answers 404 and the panel is not shown at all; a slot that was
never heard, a brain that does not answer and a slot the bridge could not give are said plainly, and nothing is invented. The same rules as the panel of STUDIO."""
from __future__ import annotations

from hydra_suite.i18n import _

SLOTS = tuple(range(8))
POLL_MS = 10000
FLAGS = ("estop_latched", "bus_off_seen", "watchdog_reset_at_start", "setup_failed_at_start", "application_confirmed", "drivers_enabled", "setup_failed_safe_state")


def _int(value: object, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def parse_slot(raw: object, slot: int) -> dict | None:
    """The answer of the server for `slot` in the shape the panel uses, or None when it is not a health answer of that slot."""
    if not isinstance(raw, dict) or raw.get("slot") != slot or not isinstance(raw.get("online"), bool):
        return None
    empty = {"online": raw["online"], "slot": slot, "heard": None, "ageMs": None, "sequence": None, "flagNames": [], "txErrors": None, "rxErrors": None, "stalls": None, "uptimeS": None}
    if not raw["online"]:
        return empty
    if raw.get("heard") is False:
        return {**empty, "heard": False}
    if raw.get("heard") is not True:
        return None
    names = raw.get("flagNames")
    if not isinstance(names, list) or len(names) > 16 or not all(isinstance(n, str) and len(n) <= 64 for n in names):
        return None
    if not (_int(raw.get("ageMs"), 0, 25400) and _int(raw.get("sequence"), 0, 255) and _int(raw.get("txErrors"), 0, 255) and _int(raw.get("rxErrors"), 0, 255)
            and _int(raw.get("stalls"), 0, 255) and _int(raw.get("uptimeS"), 0, 4080)):
        return None
    return {**empty, "heard": True, "ageMs": raw["ageMs"], "sequence": raw["sequence"], "flagNames": list(names), "txErrors": raw["txErrors"], "rxErrors": raw["rxErrors"],
            "stalls": raw["stalls"], "uptimeS": raw["uptimeS"]}


def classify(result: tuple[int, object] | None, slot: int) -> tuple[str, dict | None]:
    """("ok", reading) for a good answer; otherwise the kind of failure: "unsupported", "forbidden", "http", "malformed" or "network"."""
    if result is None:
        return "network", None
    status, body = result
    if status == 404:
        return "unsupported", None
    if status in (401, 403):
        return "forbidden", None
    if status != 200:
        return "http", None
    reading = parse_slot(body, slot)
    return ("ok", reading) if reading is not None else ("malformed", None)


def is_hidden(kinds: list[str]) -> bool:
    """True unless the server offers the panel: the route is off, the account may not read it, the answers cannot be trusted or the network is down.
    A server that answers 5xx (the bridge is silent) still shows it, with "no reading"."""
    return not any(kind in ("ok", "http") for kind in kinds)


def slot_state(reading: dict) -> str:
    if not reading["online"]:
        return "silent"
    return "heard" if reading["heard"] else "never"


def row(kind: str, reading: dict | None, slot: int) -> dict:
    """What the panel shows for one slot, with the sentences in the language of the interface."""
    title = f"{_('NODEHEALTH_SLOT')} {slot}"
    if kind != "ok" or reading is None:
        return {"slot": slot, "title": title, "state": "unknown", "stateLabel": _("NODEHEALTH_STATE_UNKNOWN"), "detail": "", "flags": ""}
    state = slot_state(reading)
    if state != "heard":
        return {"slot": slot, "title": title, "state": state, "stateLabel": _("NODEHEALTH_STATE_" + state.upper()), "detail": "", "flags": ""}
    seconds = f"{reading['ageMs'] / 1000:.1f}"
    uptime = _("NODEHEALTH_UPTIME_MORE", seconds=reading["uptimeS"]) if reading["uptimeS"] >= 4080 else _("NODEHEALTH_UPTIME", seconds=reading["uptimeS"])
    detail = " - ".join([
        _("NODEHEALTH_AGE", seconds=seconds) + " - " + _("NODEHEALTH_SEQUENCE", n=reading["sequence"]),
        _("NODEHEALTH_ERRORS", tx=reading["txErrors"], rx=reading["rxErrors"]) + " - " + _("NODEHEALTH_STALLS", n=reading["stalls"]),
        uptime,
    ])
    names = reading["flagNames"]
    flags = _("NODEHEALTH_FLAGS_NONE") if not names else ", ".join(_("NODEHEALTH_FLAG_" + n.upper()) if n in FLAGS else n for n in names)
    return {"slot": slot, "title": title, "state": "heard", "stateLabel": _("NODEHEALTH_STATE_HEARD"), "detail": detail, "flags": flags}


def rows(results: list[tuple[str, dict | None]]) -> list[dict]:
    """The rows for the eight slots, or an empty list when the panel is not shown."""
    if is_hidden([kind for kind, _reading in results]):
        return []
    return [row(kind, reading, slot) for slot, (kind, reading) in enumerate(results)]
