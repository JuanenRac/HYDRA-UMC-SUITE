# =============================================================================
# HYDRA-UMC SUITE - models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Deliberately NOT a strict dataclass schema that (de)serializes the full
# settings.json shape field-by-field. HYDRA-UMC STUDIO's own real state
# (src/store.tsx's SystemSettings/HydraController/RobotState) has many
# fields this app never needs to display or edit (UI layout prefs,
# per-integration IP/port blocks, etc.) - a strict schema would either
# have to model every one of them (large, constantly drifting out of sync
# with the real TypeScript source of truth) or silently DROP any field it
# doesn't know about on the next write-back, corrupting the real app's
# state for anyone still using the browser UI. Instead, HydraState wraps
# the raw dict as received from the server and only exposes convenience
# accessors for the handful of fields this app actually reads/writes -
# every other field passes through untouched on a round-trip.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# The 6-axis joint names every robot model in this ecosystem uses -
# see HYDRA-UMC-STUDIO's own src/store.tsx RobotState.joints shape.
JOINT_NAMES = ("j1", "j2", "j3", "j4", "j5", "j6")


class RobotView:
    """Thin, mutation-friendly view over one entry of controllers[].robots[].

    Reads/writes go straight through to the underlying dict (held by the
    owning ControllerView) - there is no separate copy to fall out of
    sync with what actually gets sent back to the server.
    """

    def __init__(self, raw: dict[str, Any]):
        self.raw = raw

    @property
    def id(self) -> str:
        return str(self.raw.get("id", ""))

    @property
    def model(self) -> str:
        return str(self.raw.get("model", "Generic (6-DOF)"))

    @property
    def role(self) -> str:
        return str(self.raw.get("role", "Idle"))

    @property
    def online(self) -> bool:
        return bool(self.raw.get("online", False))

    @property
    def joints(self) -> dict[str, float]:
        j = self.raw.get("joints") or {}
        return {name: float(j.get(name, 0.0)) for name in JOINT_NAMES}

    def set_joint(self, name: str, value: float) -> None:
        if name not in JOINT_NAMES:
            raise ValueError(f"Unknown joint {name!r} - expected one of {JOINT_NAMES}")
        joints = self.raw.setdefault("joints", {})
        joints[name] = value

    @property
    def playback_state(self) -> dict[str, Any]:
        return self.raw.get("playbackState") or {}

    @property
    def speed(self) -> float:
        return float(self.playback_state.get("speed", 100))

    def set_speed(self, value: float) -> None:
        self.raw.setdefault("playbackState", {})["speed"] = value

    @property
    def acceleration(self) -> float:
        return float(self.playback_state.get("acceleration", 100))

    def set_acceleration(self, value: float) -> None:
        self.raw.setdefault("playbackState", {})["acceleration"] = value

    @property
    def tool(self) -> str:
        return str(self.raw.get("tool", "None"))

    def __repr__(self) -> str:
        return f"RobotView(id={self.id!r}, model={self.model!r}, online={self.online})"


class ControllerView:
    """Thin view over one entry of the top-level controllers[] array."""

    def __init__(self, raw: dict[str, Any]):
        self.raw = raw

    @property
    def id(self) -> str:
        return str(self.raw.get("id", ""))

    @property
    def name(self) -> str:
        return str(self.raw.get("name", self.id))

    @property
    def ip(self) -> str:
        return str(self.raw.get("ip", ""))

    @property
    def robots(self) -> list[RobotView]:
        return [RobotView(r) for r in (self.raw.get("robots") or [])]

    def robot_by_id(self, robot_id: str) -> RobotView | None:
        for r in self.robots:
            if r.id == robot_id:
                return r
        return None

    def __repr__(self) -> str:
        return f"ControllerView(id={self.id!r}, name={self.name!r}, robots={len(self.robots)})"


class HydraState:
    """Wraps one server's full {settings, controllers, activeControllerId}
    payload - exactly the shape GET /api/settings returns and POST
    /api/settings expects back, per docs/REMOTE_API.md section 2."""

    def __init__(self, raw: dict[str, Any] | None = None):
        self.raw: dict[str, Any] = raw if raw is not None else {"settings": {}, "controllers": [], "activeControllerId": ""}

    @property
    def controllers(self) -> list[ControllerView]:
        return [ControllerView(c) for c in (self.raw.get("controllers") or [])]

    @property
    def active_controller_id(self) -> str:
        return str(self.raw.get("activeControllerId", ""))

    @property
    def active_controller(self) -> ControllerView | None:
        cid = self.active_controller_id
        for c in self.controllers:
            if c.id == cid:
                return c
        controllers = self.controllers
        return controllers[0] if controllers else None

    def to_json_dict(self) -> dict[str, Any]:
        """The exact dict to POST back / send over the settings WebSocket
        message - just the raw payload, since every accessor above
        mutates it in place rather than a detached copy."""
        return self.raw


@dataclass
class ServerInfo:
    """One entry in the discovery/connection list - see docs/REMOTE_API.md
    section 1 (GET /api/hydra-info) for the wire shape this is built from."""

    host: str
    port: int = 3000
    product: str = ""
    remote_api_version: int = 0
    app_version: str = ""
    hostname: str = ""
    controller_count: int = 0
    robot_count: int = 0
    uptime_seconds: int = 0
    nickname: str = ""  # user-assigned label, not from the server

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws"

    @property
    def display_name(self) -> str:
        return self.nickname or self.hostname or self.host

    @staticmethod
    def from_hydra_info(host: str, port: int, payload: dict[str, Any]) -> "ServerInfo":
        return ServerInfo(
            host=host,
            port=port,
            product=str(payload.get("product", "")),
            remote_api_version=int(payload.get("remoteApiVersion", 0)),
            app_version=str(payload.get("appVersion", "")),
            hostname=str(payload.get("hostname", "")),
            controller_count=int(payload.get("controllerCount", 0)),
            robot_count=int(payload.get("robotCount", 0)),
            uptime_seconds=int(payload.get("uptimeSeconds", 0)),
        )
