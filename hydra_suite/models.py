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

RACK_MAX_CAPACITY = 24


def default_rack(rack_type: str) -> dict[str, Any]:
    """Matches HYDRA-UMC-STUDIO's own createDefaultRobots() seed for one
    rack (rack1/rack2) - real defaults, not invented ones."""
    return {
        "type": rack_type,
        "capacity": RACK_MAX_CAPACITY,
        "usableSlots": [True] * RACK_MAX_CAPACITY,
        "basePickupPos": {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0, "tx": 0, "ty": 0},
    }


def default_rack_system() -> dict[str, Any]:
    """Matches HYDRA-UMC-STUDIO's own createDefaultRobots() seed for
    `rackSystem` (rack1 defaults to Input, rack2 to Output) - the same
    real shape RackConfigView.tsx's own handleReset() also writes back
    (`enabled: true` there, since Reset only exists once already
    enabled; `enabled: False` here since this is the "never configured
    at all" fallback, matching the actual seed default)."""
    return {"enabled": False, "rack1": default_rack("Input"), "rack2": default_rack("Output")}


def default_kinematic_brain_stage() -> dict[str, Any]:
    """Matches HYDRA-UMC-STUDIO's own createDefaultKinematicBrainStage()
    exactly - real seed values, not invented ones (600x400x150mm real
    table default, 6-slot ATC revolver default, etc.)."""
    return {
        "xyTable": {"x": 0, "y1": 0, "y2": 0, "z": 0, "tableSize": {"width": 600, "length": 400, "height": 150}},
        "heatedBed": {"targetTemp": 0, "currentTemp1": 24, "currentTemp2": 24, "ssrActive": False},
        "atcRevolver": {"toolCount": 6, "currentIndex": 0, "targetIndex": 0, "homed": False},
        "conveyor": {"installed": False, "running": False, "speedPercent": 0},
        "endstops": {
            "xMin": False, "xMax": False, "y1Min": False, "y1Max": False, "y2Min": False, "y2Max": False,
            "zMin": False, "zMax": False, "e0Min": False, "e0Max": False, "e1Min": False, "e1Max": False,
        },
        "fans": [False, False, False],
        "pumps": [False] * 10,
        "valves": [False] * 10,
    }


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
    def urtc_connected(self) -> bool:
        """Whether this robot's own URTC Tool Head is reachable at all
        (Tier 2 of the CAN-OTA chain, HYDRA-UMC-STUDIO's own
        `RobotState.urtcConnected`) - gates the urtcHead/urtcExpansion
        options in Flasher/Tester's own Board select (a robot slot with
        no URTC head can't reach either)."""
        return bool(self.raw.get("urtcConnected", False))

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

    @property
    def has_xy_table(self) -> bool:
        """Mirrors STUDIO's own `selectedRobot.hasXYTable` - gates whether
        a position editor (this one and STUDIO's own XYTableConfig.tsx
        equivalents) shows the extra table tx/ty fields alongside the 6
        joint angles."""
        return bool(self.raw.get("hasXYTable", False))

    def set_has_xy_table(self, value: bool) -> None:
        self.raw["hasXYTable"] = value

    @property
    def xy_table(self) -> dict[str, Any] | None:
        """HYDRA-UMC-STUDIO's own XYTable state (XYTableConfig.tsx):
        `{pos: {x,y}, tableSize: {width,length}, worldPos, worldRot,
        renderScale}` - UNLIKE `atc` above, this is a genuinely separate
        field from `hasXYTable` (STUDIO keeps both: the boolean flag AND
        this object can exist independently, e.g. right after
        `handleAddTable()` sets `hasXYTable: true` alone with no `xyTable`
        block yet - the UI's own `xyTable?.tableSize.width || 500`
        fallbacks exist precisely for that gap). Returns None, not {},
        when absent so a caller can tell "no config written yet" apart
        from "a real xyTable with all-zero fields"."""
        value = self.raw.get("xyTable")
        return value if isinstance(value, dict) else None

    def set_xy_table(self, config: dict[str, Any] | None) -> None:
        if config is None:
            self.raw.pop("xyTable", None)
        else:
            self.raw["xyTable"] = config

    @property
    def atc(self) -> dict[str, Any] | None:
        """HYDRA-UMC-STUDIO's own ATCConfig (ATCToolsConfig.tsx) - deliberately
        NOT the module()/module_enabled() {enabled: bool, ...} shape every
        other tool attachment uses. `selectedRobot.atc` on the TypeScript
        side is `undefined` when no Automatic Tool Changer is configured and
        a full ATCConfig object otherwise (type/panelGrid/revolverSlots/
        tools/revolverPos) - presence of the key IS the enabled state, there
        is no separate flag. Returns None rather than {} on the disabled
        path so a caller can tell "no ATC" apart from "an ATC with no real
        fields yet" without a second signal."""
        value = self.raw.get("atc")
        return value if isinstance(value, dict) else None

    def set_atc(self, config: dict[str, Any] | None) -> None:
        """None removes the key entirely - the real Python equivalent of
        STUDIO's own `updateRobot(id, { atc: undefined })` (disableATC()),
        not a value that would round-trip as JSON `null` and be mistaken
        for "configured with nothing in it" on the next read."""
        if config is None:
            self.raw.pop("atc", None)
        else:
            self.raw["atc"] = config

    @property
    def rack_system(self) -> dict[str, Any]:
        """HYDRA-UMC-STUDIO's own `rackSystem` (RackConfigView.tsx):
        `{enabled, rack1: RackConfig, rack2: RackConfig}` - UNLIKE `atc`
        above, this is never undefined on the TypeScript side
        (`createDefaultRobots()` always seeds a real one, `enabled`
        alone gates whether it's in use) - `RackConfigView.tsx` itself
        reads `selectedRobot.rackSystem.enabled` with no optional
        chaining at all, so a real STUDIO robot missing this field would
        crash there too. Returns the same real default STUDIO's own
        seed uses (not a value STUDIO doesn't have) if genuinely absent,
        rather than crashing this side on an edge case STUDIO's own
        source doesn't defend against either."""
        value = self.raw.get("rackSystem")
        return value if isinstance(value, dict) else default_rack_system()

    def set_rack_system(self, config: dict[str, Any]) -> None:
        self.raw["rackSystem"] = config

    def module(self, key: str) -> dict[str, Any]:
        """Generic accessor for a tool-attachment's own config block (e.g.
        `juanenCNC`/`juanenLaser`/`heatedBed`) - mirrors
        HYDRA-UMC-STUDIO's own `selectedRobot[machineType] as any` generic
        indexing (CNC.tsx/Laser.tsx/HeatedBedConfig.tsx/...) rather than a
        hardcoded property per module, so a caller can read/write any of
        these blocks the same way. Never None - callers already treat a
        missing/disabled module as `{}`/falsy `enabled`, same as the
        TypeScript side's own `moduleData?.enabled || false` pattern."""
        value = self.raw.get(key)
        return value if isinstance(value, dict) else {}

    def module_enabled(self, key: str) -> bool:
        return bool(self.module(key).get("enabled", False))

    def set_module(self, key: str, data: dict[str, Any]) -> None:
        self.raw[key] = data

    def __repr__(self) -> str:
        return f"RobotView(id={self.id!r}, model={self.model!r}, online={self.online})"


# The 4 camera type strings HYDRA-UMC-STUDIO's own store.tsx CameraType
# union allows - see that file's own CameraState interface.
CAMERA_TYPES = ("USB Vision Camera", "Thermal (MLX90640)", "Thermal (MLX90641)", "Thermal (MLX90642)")

# Matches HYDRA-UMC-STUDIO's own store.tsx RTSP_DEFAULT_PORT (real port
# 554 - the RTSP/RFC 2326 standard) - see CameraView.rtsp_port below for
# why "unset" reads as this, not 0.
RTSP_DEFAULT_PORT = 554


class CameraView:
    """Thin, mutation-friendly view over one entry of
    controllers[].cameras[] - same reasoning as RobotView. Matches
    HYDRA-UMC-STUDIO's own CameraState interface (src/store.tsx) field
    for field: id/connected/type/yoloEnabled/detections. This view only
    carries the real, server-synced METADATA (which cameras exist,
    their type, connected state) - the real MJPEG pixels themselves
    (HYDRA-UMC-VISION-STREAMER's own `stream serve`, proxied live
    through HYDRA-UMC-SERVER's `GET /api/camera/:id/stream` - real,
    verified end to end against a real USB webcam) are not
    something this metadata view fetches or renders; a real camera-pips.py
    live viewport, matching STUDIO's own CameraPIP, is a separate,
    not-yet-done piece of work here, not a hardware limitation anymore."""

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

    # --- Real IP (RTSP) camera support, mirroring HYDRA-UMC-STUDIO's own
    # CameraState (src/store.tsx) field for field - same "STUDIO ->
    # SUITE" parity that already applies to every other field on this
    # class. `assignedRobotId`/`sourceType`/`hardwareSource`/`ipHost`/
    # `rtspPort`/`rtspPath`/`ipUsername`/`ipPassword` are the exact same
    # camelCase JSON keys STUDIO reads/writes, since this raw dict is the
    # same synced settings blob any browser tab is looking at too - a
    # camera assigned/configured here shows up there unchanged, and vice
    # versa. `assignedRobotId` is stored as a real JSON number (not a
    # string) deliberately: STUDIO's own updateRobot()-on-camera-toggle
    # path does a strict `r.id === cam.assignedRobotId` comparison
    # against RobotState.id (itself a number) - a string here would
    # silently break that match from this app's own writes.
    @property
    def assigned_robot_id(self) -> int | None:
        value = self.raw.get("assignedRobotId")
        return int(value) if value is not None else None

    def set_assigned_robot_id(self, value: int | None) -> None:
        if value is None:
            self.raw.pop("assignedRobotId", None)
        else:
            self.raw["assignedRobotId"] = int(value)

    @property
    def source_type(self) -> str:
        # Undefined/absent reads as "usb" everywhere this is checked -
        # same backward-compatible default STUDIO's own store.tsx and
        # HYDRA-UMC-VISION-STREAMER's own CameraConfig both use, so every
        # camera entry saved before this field existed keeps working
        # unchanged.
        return str(self.raw.get("sourceType") or "usb")

    def set_source_type(self, value: str) -> None:
        self.raw["sourceType"] = value

    @property
    def hardware_source(self) -> str:
        """USB mode: a real V4L2 device path or index, e.g. "/dev/video0"."""
        return str(self.raw.get("hardwareSource", ""))

    def set_hardware_source(self, value: str) -> None:
        self.raw["hardwareSource"] = value

    @property
    def ip_host(self) -> str:
        """IP mode: the camera's own host/IP address."""
        return str(self.raw.get("ipHost", ""))

    def set_ip_host(self, value: str) -> None:
        self.raw["ipHost"] = value

    @property
    def rtsp_port(self) -> int:
        value = self.raw.get("rtspPort")
        return int(value) if value is not None else RTSP_DEFAULT_PORT

    def set_rtsp_port(self, value: int) -> None:
        self.raw["rtspPort"] = int(value)

    @property
    def rtsp_path(self) -> str:
        return str(self.raw.get("rtspPath", ""))

    def set_rtsp_path(self, value: str) -> None:
        self.raw["rtspPath"] = value

    @property
    def ip_username(self) -> str:
        return str(self.raw.get("ipUsername", ""))

    def set_ip_username(self, value: str) -> None:
        self.raw["ipUsername"] = value

    @property
    def ip_password(self) -> str:
        return str(self.raw.get("ipPassword", ""))

    def set_ip_password(self, value: str) -> None:
        self.raw["ipPassword"] = value

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

    @property
    def kinematic_brain_stage(self) -> dict[str, Any]:
        """HYDRA-UMC-STUDIO's own `kinematicBrainStage`
        (KinematicBrainStage.tsx) - the Kinematic Brain's OWN local
        6-axis stage (STM32H745): XY gantry + Z, heated bed, ATC
        revolver, conveyor, 12 endstops, fans/pumps/valves. UNLIKE every
        other module on `RobotView` above, this is CONTROLLER-level
        state (one Kinematic Brain per controller, not per robot) - see
        that file's own header comment. Genuinely optional on the
        TypeScript side (`kinematicBrainStage?: KinematicBrainStage`)
        with no "Enable" affordance at all if absent - STUDIO's own
        component just renders nothing (`if (!activeController ||
        !stage) return null`). In practice every real controller is
        seeded with this via `createDefaultKinematicBrainStage()` and
        it's never actually missing - returns that same real default
        here too rather than an unusable blank panel for an edge case
        neither side's own default state ever actually hits."""
        value = self.raw.get("kinematicBrainStage")
        return value if isinstance(value, dict) else default_kinematic_brain_stage()

    def set_kinematic_brain_stage(self, config: dict[str, Any]) -> None:
        self.raw["kinematicBrainStage"] = config

    @property
    def kinematic_brain(self) -> dict[str, Any]:
        """HYDRA-UMC-STUDIO's own `kinematicBrain` (`CanOtaBoardState` -
        firmwareVersion/bootloaderVersion/hardwareId/lastSeen) - the
        Kinematic Brain's own CAN-OTA firmware/identity record (Tier 0),
        DISTINCT from `kinematic_brain_stage` above (that one is its
        LIVE stage state - gantry position, heated bed, etc; this one is
        which firmware it's running). Never None - callers already treat
        a never-queried board as `{}`/falsy fields, same as STUDIO's own
        `boardState?.firmwareVersion || '?'` pattern (Flasher.tsx)."""
        value = self.raw.get("kinematicBrain")
        return value if isinstance(value, dict) else {}

    def set_kinematic_brain(self, data: dict[str, Any]) -> None:
        self.raw["kinematicBrain"] = data

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

    @property
    def can_ota_transport(self) -> str:
        """The same `settings.canOta.transport` field HYDRA-UMC STUDIO's
        own Flasher.tsx/Tester.tsx read (`'mock' | 'hardware'`) -
        deployment-level, describes what's actually wired up on this
        real CM5, not a per-session UI toggle (STUDIO itself has no
        Config screen for this either - matches that field's own
        `canOta?:` optional type). Defaults to "mock" for anything else
        (missing, or a value neither side recognizes), same as STUDIO's
        own `settings.canOta?.transport === 'hardware'` strict-equality
        check - only an EXACT "hardware" ever reaches the real path."""
        raw_can_ota = (self.raw.get("settings") or {}).get("canOta") or {}
        return "hardware" if raw_can_ota.get("transport") == "hardware" else "mock"

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
