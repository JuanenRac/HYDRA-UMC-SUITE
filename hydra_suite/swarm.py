# =============================================================================
# HYDRA-UMC SUITE - swarm.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The swarm view and the combined mode, with no Qt and no network.
#
# - The swarm view is one table with every robot of every server the program is connected to, at the same time (the
#   rest of the program shows the active server only): where it is, whether it answers, whether it plays, who holds
#   its reservation, and with which robots it is combined. It is off until the operator switches it on; the limits
#   (rows shown, largest group of combined robots) are in assets/swarm_view.json.
# - The combined mode is the list `combinedWith` of a robot: what Play, Pause and Stop do to it, the server does to
#   the robots listed there too. Only the robot that starts the combination keeps the list (HYDRA-UMC-STUDIO and the
#   server do the same); a robot named in the list of another is "led" by it. The list never repeats an id, never
#   holds the robot itself, and never grows past the limit of the file.
# =============================================================================
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

CONFIG_PATH = Path(__file__).resolve().parent.parent / "assets" / "swarm_view.json"

_FALLBACK = {"enabledByDefault": False, "combinedModeByDefault": False, "maxRows": 500, "maxCombined": 8, "filters": ["all", "online", "playing", "attention"]}


def load_settings(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """The limits and defaults of the file; the built-in ones when it is missing or damaged."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(_FALLBACK)
    if not isinstance(data, dict):
        return dict(_FALLBACK)
    merged = dict(_FALLBACK)
    for key, fallback in _FALLBACK.items():
        value = data.get(key, fallback)
        if isinstance(fallback, bool):
            merged[key] = value if isinstance(value, bool) else fallback
        elif isinstance(fallback, int):
            merged[key] = value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else fallback
        else:
            merged[key] = value if isinstance(value, list) and value else fallback
    return merged


SETTINGS = load_settings()
FILTERS: tuple[str, ...] = tuple(str(f) for f in SETTINGS["filters"])
MAX_ROWS: int = SETTINGS["maxRows"]
MAX_COMBINED: int = SETTINGS["maxCombined"]


@dataclass
class SwarmServer:
    """What the view needs from one connection (the bridge fills it from the connection)."""

    conn_id: str
    name: str
    status: str = "connected"            # "connected", "connecting", "disconnected", "login_failed", ...
    robots: list[dict[str, Any]] = field(default_factory=list)   # the raw dicts of the robots (all controllers of the server)
    claims: dict[int, str] = field(default_factory=dict)         # robot id -> account that holds the reservation
    active: bool = False


def _int_id(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().lstrip("-").isdigit():
        return int(raw)
    return None


def combined_ids(raw_robot: dict[str, Any]) -> list[int]:
    """The ids in `combinedWith` of a robot, without repeats and without the robot itself."""
    own = _int_id(raw_robot.get("id"))
    value = raw_robot.get("combinedWith")
    result: list[int] = []
    if isinstance(value, list):
        for item in value:
            number = _int_id(item)
            if number is not None and number != own and number not in result:
                result.append(number)
    return result


def playback_key(raw_robot: dict[str, Any]) -> str:
    state = raw_robot.get("playbackState")
    state = state if isinstance(state, dict) else {}
    if state.get("isPlaying"):
        return "paused" if state.get("isPaused") else "playing"
    return "finished" if state.get("isFinished") else "idle"


def source_key(raw_robot: dict[str, Any]) -> str:
    """Same rule as RobotView.motion_source: offline, simulated (no tool controller) or live."""
    if not raw_robot.get("online"):
        return "offline"
    return "live" if raw_robot.get("urtcConnected") else "simulated"


def build_rows(servers: Iterable[SwarmServer], limit: int = MAX_ROWS) -> list[dict[str, Any]]:
    """One row per robot of every server, the servers in the order given and the robots by id. A server that does not answer
    has one row of its own (no robot), so it does not vanish from the table."""
    rows: list[dict[str, Any]] = []
    for server in servers:
        leaders: dict[int, list[int]] = {}
        for raw in server.robots:
            leader = _int_id(raw.get("id"))
            if leader is None:
                continue
            for member in combined_ids(raw):
                leaders.setdefault(member, []).append(leader)
        robots = sorted(server.robots, key=lambda r: (_int_id(r.get("id")) is None, _int_id(r.get("id")) or 0))
        if not robots:
            rows.append({"connId": server.conn_id, "server": server.name, "status": server.status, "active": server.active, "robotId": -1, "robot": "", "model": "",
                         "source": "none", "enabled": True, "playback": "none", "holder": "", "combinedWith": [], "ledBy": [], "points": 0})
        for raw in robots:
            robot_id = _int_id(raw.get("id"))
            if robot_id is None:
                continue
            points = raw.get("recordedPoints")
            rows.append({
                "connId": server.conn_id,
                "server": server.name,
                "status": server.status,
                "active": server.active,
                "robotId": robot_id,
                "robot": str(raw.get("name") or f"#{robot_id}"),
                "model": str(raw.get("model") or ""),
                "source": source_key(raw),
                "enabled": raw.get("enabled") is not False,
                "playback": playback_key(raw),
                "holder": server.claims.get(robot_id, ""),
                "combinedWith": combined_ids(raw),
                "ledBy": leaders.get(robot_id, []),
                "points": len(points) if isinstance(points, list) else 0,
            })
    return rows[: max(1, limit)]


def needs_attention(row: dict[str, Any], my_account: str | None = None) -> bool:
    """A robot the operator should look at: offline, in safe mode, held by another account, or on a server that does not answer."""
    if row["status"] not in ("connected", "connecting"):
        return True
    if row["source"] == "none":
        return False
    if row["source"] == "offline" or not row["enabled"]:
        return True
    return bool(row["holder"]) and row["holder"] != (my_account or "")


def filter_rows(rows: list[dict[str, Any]], mode: str = "all", text: str = "", my_account: str | None = None) -> list[dict[str, Any]]:
    """The rows of one filter ("all", "online", "playing", "attention") that also contain `text` in the server, robot or model."""
    needle = text.strip().lower()
    kept: list[dict[str, Any]] = []
    for row in rows:
        if mode == "online" and row["source"] in ("offline", "none"):
            continue
        if mode == "playing" and row["playback"] not in ("playing", "paused"):
            continue
        if mode == "attention" and not needs_attention(row, my_account):
            continue
        if needle and needle not in f"{row['server']} {row['robot']} {row['model']} {row['holder']}".lower():
            continue
        kept.append(row)
    return kept


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Counts for the line above the table."""
    servers = {row["connId"] for row in rows}
    reachable = {row["connId"] for row in rows if row["status"] == "connected"}
    robots = [row for row in rows if row["source"] != "none"]
    return {
        "servers": len(servers),
        "serversReachable": len(reachable),
        "robots": len(robots),
        "online": sum(1 for r in robots if r["source"] != "offline"),
        "playing": sum(1 for r in robots if r["playback"] in ("playing", "paused")),
        "held": sum(1 for r in robots if r["holder"]),
        "combined": sum(1 for r in robots if r["combinedWith"]),
    }


# --- combined mode -----------------------------------------------------------------------------------------------

def combine_candidates(robots: Iterable[dict[str, Any]], selected_id: int) -> list[dict[str, Any]]:
    """The robots a robot can be combined with: the other robots of the same server that answer, by id."""
    options: list[dict[str, Any]] = []
    for raw in robots:
        robot_id = _int_id(raw.get("id"))
        if robot_id is None or robot_id == selected_id or not raw.get("online"):
            continue
        options.append({"id": robot_id, "name": str(raw.get("name") or f"#{robot_id}"), "model": str(raw.get("model") or "")})
    return sorted(options, key=lambda o: o["id"])


def toggle_combined(current: Iterable[Any], robot_id: int, on: bool, own_id: int | None = None, limit: int = MAX_COMBINED) -> list[int]:
    """The new `combinedWith` after switching one robot on or off: no repeats, never the robot itself, never past `limit`
    (a robot that would pass it is left out, and the list is returned as it was)."""
    result: list[int] = []
    for item in current:
        number = _int_id(item)
        if number is not None and number != own_id and number not in result:
            result.append(number)
    if robot_id == own_id:
        return result
    if on:
        if robot_id not in result and len(result) < limit:
            result.append(robot_id)
    else:
        result = [n for n in result if n != robot_id]
    return result
