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

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


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
        # A NaN/Infinity value can reach this dict two ways this app doesn't
        # control: a server payload authored by something other than SUITE
        # itself (json.loads() happily parses the literal tokens "NaN"/
        # "Infinity"/"-Infinity" into float('nan')/inf by default - that's
        # valid Python-flavored JSON, not a parse error), or a value already
        # sitting in a swarm this app connected to mid-corruption. Silently
        # forwarding it further downstream is the real bug this guards
        # against: RotaryKnob.setValue() happens to clamp NaN/Inf away via
        # Python's own min()/max() NaN semantics, but JointRow.set_value()'s
        # own `int(value * SLIDER_SCALE)` does NOT - int() raises ValueError
        # on NaN and OverflowError on +/-Infinity, which crashes the whole
        # _refresh_controls() call (and, on the "Jog to point" path, would
        # also make trajectory_panel.py's own _on_record() capture the
        # invalid value and hand it right back to set_joint() below).
        # Substituting 0.0 here keeps the UI alive and stops a bad value
        # already in the tree from being echoed straight back to the server
        # on the very next push_active_state() with a clean bill of health.
        j = self.raw.get("joints") or {}
        result: dict[str, float] = {}
        for name in JOINT_NAMES:
            value = float(j.get(name, 0.0))
            if not math.isfinite(value):
                logger.warning("RobotView %s: non-finite joint %s=%r from server, substituting 0.0", self.id, name, value)
                value = 0.0
            result[name] = value
        return result

    def set_joint(self, name: str, value: float) -> None:
        if name not in JOINT_NAMES:
            raise ValueError(f"Unknown joint {name!r} - expected one of {JOINT_NAMES}")
        if not math.isfinite(value):
            # Every real caller today (robot_control.py's own RotaryKnob/
            # QSlider jog, trajectory_panel.py's own recorded-point replay)
            # is bounded and can never actually produce this - this is a
            # defense-in-depth guard against a future/third-party caller of
            # this public API, not a UI input path that's been observed to
            # trigger it. A NaN/Infinity joint value pushed to the server
            # over POST /api/settings or the WebSocket is exactly the class
            # of malformed input that can hang the server's own kinematic
            # engine, so this app must never be the one to author one.
            raise ValueError(f"Refusing to set joint {name!r} to non-finite value {value!r}")
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


# The 4 camera type strings HYDRA-UMC-STUDIO's own store.tsx CameraType
# union allows - see that file's own CameraState interface.
CAMERA_TYPES = ("USB Vision Camera", "Thermal (MLX90640)", "Thermal (MLX90641)", "Thermal (MLX90642)")


class CameraView:
    """Thin, mutation-friendly view over one entry of
    controllers[].cameras[] - same reasoning as RobotView. Matches
    HYDRA-UMC-STUDIO's own CameraState interface (src/store.tsx) field
    for field: id/connected/type/yoloEnabled/detections. The "video"
    itself is a UI placeholder on BOTH sides of this ecosystem (see
    CamerasView.tsx's own header) - no real camera hardware/stream
    exists anywhere in this ecosystem yet, so this view only carries the
    real, server-synced METADATA (which cameras exist, their type,
    connected state), not pixels."""

    def __init__(self, raw: dict[str, Any]):
        self.raw = raw

    @property
    def id(self) -> int:
        return int(self.raw.get("id", 0))

    @property
    def connected(self) -> bool:
        return bool(self.raw.get("connected", False))

    def set_connected(self, value: bool) -> None:
        self.raw["connected"] = value
        if not value:
            # Mirrors HYDRA-UMC-STUDIO's own toggleConnection() - YOLO
            # inference can't meaningfully stay "on" for a camera with
            # no connection.
            self.raw["yoloEnabled"] = False

    @property
    def camera_type(self) -> str:
        return str(self.raw.get("type", CAMERA_TYPES[0]))

    def set_camera_type(self, value: str) -> None:
        self.raw["type"] = value

    @property
    def yolo_enabled(self) -> bool:
        return bool(self.raw.get("yoloEnabled", False))

    def set_yolo_enabled(self, value: bool) -> None:
        self.raw["yoloEnabled"] = value

    def __repr__(self) -> str:
        return f"CameraView(id={self.id!r}, connected={self.connected}, type={self.camera_type!r})"


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

    @property
    def cameras(self) -> list[CameraView]:
        return [CameraView(c) for c in (self.raw.get("cameras") or [])]

    def __repr__(self) -> str:
        return f"ControllerView(id={self.id!r}, name={self.name!r}, robots={len(self.robots)})"


class HydraState:
    """Wraps one server's full {settings, controllers, activeControllerId}
    payload - exactly the shape GET /api/settings returns and POST
    /api/settings expects back, per HYDRA-UMC-SERVER/docs/REMOTE_API.md
    section 2 (moved there from HYDRA-UMC-STUDIO's own docs/ when the
    headless backend was split into its own repo)."""

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

    @property
    def ai_hailo(self) -> dict[str, str]:
        """The same `settings.aiHailo` field HYDRA-UMC STUDIO's own
        Config > AI/Hailo tab reads/writes (store.tsx) - this is the
        SAME server-persisted settings tree both apps share (GET/POST
        /api/settings), not a separate SUITE-only concept, so a change
        made in STUDIO's Config shows up here live too. Defaults match
        STUDIO's own client-side defaults exactly (visionDevice=hailo8,
        cognitiveDevice=none) so a settings.json that predates this
        field (nobody has opened Config > AI/Hailo yet) reads the same
        real-world default both apps already assume."""
        raw_ai = (self.raw.get("settings") or {}).get("aiHailo") or {}
        return {
            "visionDevice": raw_ai.get("visionDevice") or "hailo8",
            "cognitiveDevice": raw_ai.get("cognitiveDevice") or "none",
        }

    def to_json_dict(self) -> dict[str, Any]:
        """The exact dict to POST back / send over the settings WebSocket
        message - just the raw payload, since every accessor above
        mutates it in place rather than a detached copy."""
        return self.raw


@dataclass
class ServerInfo:
    """One entry in the discovery/connection list - see
    HYDRA-UMC-SERVER/docs/REMOTE_API.md section 1 (GET /api/hydra-info)
    for the wire shape this is built from."""

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
    # Credentials are always entered by the operator. Production bootstrap no
    # longer provides a source-known administrator account to discovered peers.
    username: str = ""
    password: str = ""

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def ws_url(self, token: str | None = None) -> str:
        base = f"ws://{self.host}:{self.port}/ws"
        # remoteApiVersion=2 declares this connection understands a real
        # targeted delta (server.ts's own per-connection `schema`, see
        # DISEÑO_SYNC_DELTAS.txt section 3) - a server that doesn't
        # recognize the param (or is an older deployment) just keeps
        # sending the full tree under "delta" like before, so this is safe
        # to always send once this app's own net/client.py understands the
        # real delta shape (see _handle_message()'s own schema==2 branch).
        return f"{base}?token={token}&remoteApiVersion=2" if token else base

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
