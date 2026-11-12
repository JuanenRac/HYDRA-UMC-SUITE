# =============================================================================
# HYDRA-UMC SUITE - panel_logic/twin_feed.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The live state the twin pushes, read through the server: the twin's own socket asks for a header that only the server holds the right to send, so the
# server opens it with the signed-in person's token and passes on what it pushes (the same panel as in HYDRA-UMC STUDIO). Watching is OFF by default and a
# choice of this computer (kept in the configuration file, never sent anywhere). This file is the part without any window toolkit: the preference, how a
# frame is read, the state built from the frames, what a close code means and the lines of the screen.
# =============================================================================
from __future__ import annotations

import json

from hydra_suite.i18n import _

CONFIG_KEY = "twin_feed"
#: Seconds before the socket is opened again after it dropped for a reason that is worth retrying.
RECONNECT_S = 5.0

END_DENIED = "denied"  # the session was refused: sign in again, never retry with the same token
END_NOT_AVAILABLE = "not_available"  # the server cannot pass the twin on now (not configured, or too many panels)
END_UNAVAILABLE = "unavailable"  # the twin could not be reached: worth a retry
END_CLOSED = "closed"


def watching_from_config(config: object) -> bool:
    """Whether this computer watches the twin: only a stored True switches it on; anything else (or a damaged file) is off."""
    return isinstance(config, dict) and config.get(CONFIG_KEY) is True


def config_update(on: bool) -> dict:
    return {CONFIG_KEY: bool(on)}


def empty_state() -> dict:
    return {"source": None, "robot_id": None, "joints": 0, "sequence": None, "status": None, "vehicles": {}, "frames": 0}


def parse_frame(raw: object) -> dict | None:
    """One frame of the twin; None when it is not JSON or is a kind this window does not know (it is ignored, never a reason to drop the connection)."""
    try:
        data = json.loads(raw if isinstance(raw, (str, bytes, bytearray)) else str(raw))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("error"), str):
        return {"kind": "error", "message": data["error"]}
    kind = data.get("type")
    if kind == "twin_state":
        state = data.get("state")
        if not isinstance(state, dict) or state.get("source") not in ("real", "simulated") or not isinstance(state.get("joint_states"), list):
            return None
        sequence = state.get("sequence")
        sequence = sequence if type(sequence) is int and sequence >= 0 else None
        robot_id = state.get("robot_id")
        return {"kind": "state", "source": state["source"], "robot_id": robot_id if isinstance(robot_id, str) else None, "joints": len(state["joint_states"]), "sequence": sequence}
    if kind == "status" and isinstance(data.get("code"), str):
        message = data.get("message")
        return {"kind": "status", "code": data["code"], "message": message if isinstance(message, str) else None}
    if kind == "uav_state" and isinstance(data.get("state"), dict) and isinstance(data["state"].get("robot_id"), str):
        return {"kind": "uav_state", "robot_id": data["state"]["robot_id"]}
    if kind == "uav_status" and isinstance(data.get("robot_id"), str) and isinstance(data.get("code"), str):
        return {"kind": "uav_status", "robot_id": data["robot_id"], "code": data["code"]}
    return None


def apply_frame(state: dict, frame: dict) -> dict:
    """The state after one more frame. A state older than the last one of the same robot (a lower sequence) is dropped; the state given is never changed."""
    frames = state["frames"] + 1
    kind = frame["kind"]
    if kind == "state":
        if frame["sequence"] is not None and state["sequence"] is not None and state["robot_id"] == frame["robot_id"] and frame["sequence"] < state["sequence"]:
            return state
        return dict(state, source=frame["source"], robot_id=frame["robot_id"], joints=frame["joints"], sequence=frame["sequence"], status=None, frames=frames)
    if kind == "status":
        return dict(state, status={"code": frame["code"], "message": frame["message"]}, frames=frames)
    if kind == "uav_state":
        return dict(state, vehicles=dict(state["vehicles"], **{frame["robot_id"]: {"stale": False}}), frames=frames)
    if kind == "uav_status":
        return dict(state, vehicles=dict(state["vehicles"], **{frame["robot_id"]: {"stale": frame["code"] == "stale"}}), frames=frames)
    return state


def end_for_close_code(code: object) -> str:
    if code == 1008:
        return END_DENIED
    if code == 1013:
        return END_NOT_AVAILABLE
    if code == 1011:
        return END_UNAVAILABLE
    return END_CLOSED


def retries(end: str) -> bool:
    """Whether the socket is opened again after a close: not after a refused session or a server that cannot pass the twin on."""
    return end in (END_UNAVAILABLE, END_CLOSED)


_END_KEY = {END_DENIED: "TWINLIVE_DENIED", END_NOT_AVAILABLE: "TWINLIVE_NOT_AVAILABLE", END_UNAVAILABLE: "TWINLIVE_UNAVAILABLE", END_CLOSED: "TWINLIVE_CLOSED"}


def view(watching: bool, link: str, state: dict) -> dict:
    """What the screen shows; every key is present whatever the link, so the screen never binds to an undefined text."""
    if not watching:
        link_text = _("TWINLIVE_OFF")
    elif link == "connecting":
        link_text = _("TWINLIVE_CONNECTING")
    elif link == "live":
        link_text = _("TWINLIVE_LIVE")
    else:
        link_text = _(_END_KEY.get(link, "TWINLIVE_CLOSED"))
    live = watching and link == "live"
    if live and state["source"] is not None:
        state_text = _("TWINLIVE_STATE_REAL" if state["source"] == "real" else "TWINLIVE_STATE_SIMULATED", joints=state["joints"])
    elif live:
        state_text = _("TWINLIVE_NO_STATE")
    else:
        state_text = ""
    status_text = _("TWINLIVE_STATUS", code=state["status"]["code"]) if live and state["status"] else ""
    vehicles = state["vehicles"]
    vehicles_text = _("TWINLIVE_VEHICLES", count=len(vehicles), stale=sum(1 for v in vehicles.values() if v["stale"])) if live and vehicles else ""
    return {"watching": bool(watching), "link": link_text, "state": state_text, "status": status_text, "vehicles": vehicles_text}
