# =============================================================================
# HYDRA-UMC SUITE - access.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Who may move a robot, and how far: the controller id of this program, the reservations of
# robots, the safety limits the server reports, and the Live or Sim mode of each robot. No Qt
# and no network in here, so every rule is tested without a server.
#
# - The controller id: a reservation belongs to an account and, when the client names one, to a
#   controller (one window, one tab, one phone, one program). The same account on another
#   controller is refused. This program picks its id once, when it starts, and sends it with
#   every claim, release, jog arming and command.
# - The limits (size of a jog, range of an absolute jog, hottest bed target, optional arming of
#   the jog, mandatory controller id) live in the server: GET /api/safety-limits, changed by an
#   administrator with PUT /api/admin/safety-limits. The defaults here are the conservative ones
#   of the server itself, used until it has answered.
# - Live or Sim: in Sim, nothing that moves a robot or switches something on is sent from this
#   program. STOP, pause and the harmless settings still go through. The default is Live.
# =============================================================================
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field

CONTROLLER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def is_valid_controller_id(value: object) -> bool:
    """What the server accepts: 1 to 64 characters of letters, digits and . _ : -"""
    return isinstance(value, str) and CONTROLLER_ID_PATTERN.fullmatch(value) is not None


def generate_controller_id(rng: random.Random | None = None) -> str:
    """A fresh id: "suite-" and ten letters or digits."""
    chooser = rng or random.SystemRandom()
    return "suite-" + "".join(chooser.choice(_ID_ALPHABET) for _ in range(10))


_controller_id: str | None = None


def get_controller_id() -> str:
    """The id of this program, chosen once and kept until it closes."""
    global _controller_id
    if _controller_id is None or not is_valid_controller_id(_controller_id):
        _controller_id = generate_controller_id()
    return _controller_id


def reset_controller_id(value: str | None = None) -> None:
    """Tests: forgets the chosen id (or sets one)."""
    global _controller_id
    _controller_id = value


# --- reservations -------------------------------------------------------------------------------------------

CONFLICT_CODES = ("other-account", "other-controller", "controller-id-required")


def conflict_code_of(body: object) -> str | None:
    """The `code` of an error body when it is one of the reservation refusals, otherwise None."""
    if not isinstance(body, dict):
        return None
    code = body.get("code")
    return code if isinstance(code, str) and code in CONFLICT_CODES else None


@dataclass
class ClaimEntry:
    robot_id: int
    robot_name: str | None = None
    cell_id: str | None = None
    owner_id: str | None = None
    owner_username: str = "?"
    # The controller that holds it; None for a reservation made without one.
    controller_id: str | None = None
    claimed_at: float | None = None
    expires_at: float | None = None
    # Until when the jog of this robot is armed (the server puts it in every reservation of GET /api/claims
    # and of the `claims` message); None when it is not armed or the server predates the field.
    jog_armed_until: float | None = None

    def seconds_left(self, now: float | None = None) -> int | None:
        """Seconds left of the reservation, never negative; None when it has no expiry."""
        if self.expires_at is None:
            return None
        current = time.time() * 1000 if now is None else now
        return max(0, round((self.expires_at - current) / 1000))


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() != "" else None


def _millis(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        from datetime import datetime

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
        except ValueError:
            return None
    return None


def parse_claims(body: object) -> list[ClaimEntry]:
    """The reservations of GET /api/claims; entries that are not objects with a robot id are dropped."""
    listed = body.get("claims") if isinstance(body, dict) else None
    if not isinstance(listed, list):
        return []
    out: list[ClaimEntry] = []
    for raw in listed:
        if not isinstance(raw, dict):
            continue
        robot_id = raw.get("robotId")
        if isinstance(robot_id, bool) or not isinstance(robot_id, (int, float)):
            continue
        out.append(
            ClaimEntry(
                robot_id=int(robot_id),
                robot_name=_text(raw.get("robotName")),
                cell_id=_text(raw.get("cellId")),
                owner_id=_text(raw.get("ownerId")),
                owner_username=_text(raw.get("ownerUsername")) or "?",
                controller_id=_text(raw.get("controllerId")),
                claimed_at=_millis(raw.get("claimedAt")),
                expires_at=_millis(raw.get("expiresAt")),
                jog_armed_until=_millis(raw.get("jogArmedUntil")),
            )
        )
    return out


def claim_standing(claim: ClaimEntry | None, my_controller: str, my_username: str | None) -> str:
    """Where a robot stands for this program: "free", "mine" (held by this very program), "other-controller"
    (the same account on another controller) or "other-account". A reservation without a controller id is
    mine when the account is."""
    if claim is None:
        return "free"
    if claim.controller_id is not None:
        if claim.controller_id == my_controller:
            return "mine"
        return "other-controller" if my_username is not None and claim.owner_username == my_username else "other-account"
    return "mine" if my_username is not None and claim.owner_username == my_username else "other-account"


def failure_code_for(status: int, server_code: str | None) -> str:
    """The failure of a refused request, refined by the stable `code` of the answer when the server gave one:
    "claim_other_account", "claim_other_controller", "claim_controller_required", "jog_not_armed",
    "revision_changed" (412: the robot changed since this program read it), or the plain
    class of the status ("network", "session_expired", "forbidden", "not_found", "claimed", "rejected", "server")."""
    if server_code == "other-account":
        return "claim_other_account"
    if server_code == "other-controller":
        return "claim_other_controller"
    if server_code == "controller-id-required":
        return "claim_controller_required"
    if server_code == "jog-not-armed":
        return "jog_not_armed"
    if server_code == "revision-mismatch" or status == 412:
        return "revision_changed"
    if status == 0:
        return "network"
    if status == 401:
        return "session_expired"
    if status == 403:
        return "forbidden"
    if status == 404:
        return "not_found"
    if status == 409:
        return "claimed"
    if status >= 500:
        return "server"
    return "rejected"


# --- safety limits ------------------------------------------------------------------------------------------


@dataclass
class SafetyLimits:
    arm_required: bool = False
    arm_ttl_ms: float = 60_000
    jog_default_amount: float = 100
    jog_default_absolute: float = 1000
    # model key -> {"maxAmount": x, "maxAbsolute": y}
    jog_models: dict[str, dict[str, float]] = field(default_factory=dict)
    bed_default_c: float = 110
    # model key -> bedMaxC
    bed_models: dict[str, float] = field(default_factory=dict)
    require_controller_id: bool = False


@dataclass
class HardLimits:
    jog_max_amount: float = 1000
    jog_max_absolute: float = 10_000
    arm_ttl_min_ms: float = 1000
    arm_ttl_max_ms: float = 600_000
    bed_max_c: float = 300


@dataclass
class SafetyState:
    limits: SafetyLimits = field(default_factory=SafetyLimits)
    defaults: SafetyLimits = field(default_factory=SafetyLimits)
    hard: HardLimits = field(default_factory=HardLimits)


def model_key(model: object) -> str:
    """"Parol6 (6-DOF)" and "parol6" name the same model."""
    return str(model or "").split("(")[0].strip().lower()


def _positive(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number == number and number not in (float("inf"), float("-inf")) and number > 0 else None


def _read_limits(raw: object, fallback: SafetyLimits) -> SafetyLimits:
    if not isinstance(raw, dict):
        return fallback
    jog = raw.get("jog") if isinstance(raw.get("jog"), dict) else {}
    temperature = raw.get("temperature") if isinstance(raw.get("temperature"), dict) else {}
    claims = raw.get("claims") if isinstance(raw.get("claims"), dict) else {}
    jog_default = jog.get("default") if isinstance(jog.get("default"), dict) else {}
    temp_default = temperature.get("default") if isinstance(temperature.get("default"), dict) else {}
    jog_models: dict[str, dict[str, float]] = {}
    if isinstance(jog.get("models"), dict):
        for key, entry in jog["models"].items():
            name = model_key(key)
            if not name or not isinstance(entry, dict):
                continue
            picked: dict[str, float] = {}
            for field_name in ("maxAmount", "maxAbsolute"):
                value = _positive(entry.get(field_name))
                if value is not None:
                    picked[field_name] = value
            jog_models[name] = picked
    bed_models: dict[str, float] = {}
    if isinstance(temperature.get("models"), dict):
        for key, entry in temperature["models"].items():
            name = model_key(key)
            value = _positive(entry.get("bedMaxC")) if isinstance(entry, dict) else None
            if name and value is not None:
                bed_models[name] = value
    return SafetyLimits(
        arm_required=jog["armRequired"] if isinstance(jog.get("armRequired"), bool) else fallback.arm_required,
        arm_ttl_ms=_positive(jog.get("armTtlMs")) or fallback.arm_ttl_ms,
        jog_default_amount=_positive(jog_default.get("maxAmount")) or fallback.jog_default_amount,
        jog_default_absolute=_positive(jog_default.get("maxAbsolute")) or fallback.jog_default_absolute,
        jog_models=jog_models,
        bed_default_c=_positive(temp_default.get("bedMaxC")) or fallback.bed_default_c,
        bed_models=bed_models,
        require_controller_id=claims["requireControllerId"] if isinstance(claims.get("requireControllerId"), bool) else fallback.require_controller_id,
    )


def parse_safety_limits(body: object) -> SafetyState:
    """The answer of GET /api/safety-limits (or of the PUT, which carries the same fields); anything unreadable
    keeps the conservative defaults."""
    if not isinstance(body, dict):
        return SafetyState()
    base = SafetyLimits()
    hard_raw = body.get("hardLimits") if isinstance(body.get("hardLimits"), dict) else {}
    ttl = hard_raw.get("armTtlMs") if isinstance(hard_raw.get("armTtlMs"), dict) else {}
    defaults = HardLimits()
    return SafetyState(
        limits=_read_limits(body.get("limits"), base),
        defaults=_read_limits(body.get("defaults"), base),
        hard=HardLimits(
            jog_max_amount=_positive(hard_raw.get("jogMaxAmount")) or defaults.jog_max_amount,
            jog_max_absolute=_positive(hard_raw.get("jogMaxAbsolute")) or defaults.jog_max_absolute,
            arm_ttl_min_ms=_positive(ttl.get("min")) or defaults.arm_ttl_min_ms,
            arm_ttl_max_ms=_positive(ttl.get("max")) or defaults.arm_ttl_max_ms,
            bed_max_c=_positive(hard_raw.get("bedMaxC")) or defaults.bed_max_c,
        ),
    )


def jog_limits_for(limits: SafetyLimits, model: object) -> tuple[float, float]:
    """(largest relative jog, largest absolute position) that apply to a model: its own entry over the default."""
    own = limits.jog_models.get(model_key(model), {})
    return own.get("maxAmount", limits.jog_default_amount), own.get("maxAbsolute", limits.jog_default_absolute)


def bed_max_for(limits: SafetyLimits, model: object) -> float:
    """The heated-bed ceiling that applies to a model, in degrees Celsius."""
    return limits.bed_models.get(model_key(model), limits.bed_default_c)


def highest_bed_max(limits: SafetyLimits) -> float:
    """The hottest bed target any model may be given, for a panel that has no single robot."""
    return max([limits.bed_default_c, *limits.bed_models.values()])


def clamp_bed_target(value: object, ceiling: float) -> int:
    """A whole, finite target inside 0..ceiling (anything else becomes 0)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or value in (float("inf"), float("-inf")):
        return 0
    return int(min(ceiling, max(0, round(value))))


@dataclass(frozen=True)
class JogCheck:
    ok: bool
    limit: float
    kind: str | None  # "amount" | "absolute" | None


def check_jog(limits: SafetyLimits, model: object, params: dict | None) -> JogCheck:
    """Whether a jog is inside the limits of the model before it is sent. A relative jog is bounded by its amount,
    an absolute one by the target position, in either direction. The server checks again; this only spares the
    trip and says why."""
    max_amount, max_absolute = jog_limits_for(limits, model)
    params = params or {}
    amount = params.get("amount")
    value = float(amount) if isinstance(amount, (int, float)) and not isinstance(amount, bool) else 0.0
    if params.get("absolute") is True:
        return JogCheck(abs(value) <= max_absolute, max_absolute, None if abs(value) <= max_absolute else "absolute")
    return JogCheck(abs(value) <= max_amount, max_amount, None if abs(value) <= max_amount else "amount")


def is_armed(armed_until: float | None, now: float | None = None) -> bool:
    """Whether an arming is still running (milliseconds since the epoch, as the server reports it)."""
    current = time.time() * 1000 if now is None else now
    return isinstance(armed_until, (int, float)) and not isinstance(armed_until, bool) and armed_until > current


# --- the form of the administration screen ---------------------------------------------------------------------


def _number(raw: object, maximum: float) -> tuple[float | None, str | None]:
    """(value, problem) of one typed number: problem is "number" or "range"."""
    text = str(raw).strip()
    if text == "":
        return None, "number"
    try:
        value = float(text)
    except ValueError:
        return None, "number"
    if value != value or value in (float("inf"), float("-inf")):
        return None, "number"
    if value <= 0 or value > maximum:
        return None, "range"
    return value, None


def build_patch(form: dict, hard: HardLimits) -> dict:
    """Turns the form of the administration screen into the body of PUT /api/admin/safety-limits, checking every
    number against the hard ceilings. Returns {"ok": True, "patch": {...}} or {"ok": False, "problem": "number" |
    "range" | "model" | "duplicate", "field": name}.

    The form: armRequired, armTtlSeconds, requireControllerId, defaultMaxAmount, defaultMaxAbsolute,
    defaultBedMaxC (typed text or numbers) and rows: [{model, maxAmount, maxAbsolute, bedMaxC}] (empty text means
    "use the default")."""

    def fail(problem: str, field_name: str) -> dict:
        return {"ok": False, "problem": problem, "field": field_name}

    ttl_text = str(form.get("armTtlSeconds", "")).strip()
    try:
        ttl_ms = round(float(ttl_text) * 1000)
    except ValueError:
        return fail("number", "armTtl")
    if ttl_ms < hard.arm_ttl_min_ms or ttl_ms > hard.arm_ttl_max_ms:
        return fail("range", "armTtl")
    amount, problem = _number(form.get("defaultMaxAmount", ""), hard.jog_max_amount)
    if problem:
        return fail(problem, "defaultMaxAmount")
    absolute, problem = _number(form.get("defaultMaxAbsolute", ""), hard.jog_max_absolute)
    if problem:
        return fail(problem, "defaultMaxAbsolute")
    bed, problem = _number(form.get("defaultBedMaxC", ""), hard.bed_max_c)
    if problem:
        return fail(problem, "defaultBedMaxC")

    jog_models: dict[str, dict[str, float]] = {}
    temp_models: dict[str, dict[str, float]] = {}
    seen: set[str] = set()
    for row in form.get("rows", []) or []:
        key = model_key(row.get("model", ""))
        if not key:
            return fail("model", "model")
        if key in seen:
            return fail("duplicate", key)
        seen.add(key)
        entry: dict[str, float] = {}
        for name, maximum, field_name in (("maxAmount", hard.jog_max_amount, "maxAmount"), ("maxAbsolute", hard.jog_max_absolute, "maxAbsolute")):
            if str(row.get(name, "")).strip() != "":
                value, problem = _number(row.get(name), maximum)
                if problem or value is None:
                    return fail(problem or "number", f"{key}.{field_name}")
                entry[name] = value
        if entry:
            jog_models[key] = entry
        if str(row.get("bedMaxC", "")).strip() != "":
            value, problem = _number(row.get("bedMaxC"), hard.bed_max_c)
            if problem or value is None:
                return fail(problem or "number", f"{key}.bedMaxC")
            temp_models[key] = {"bedMaxC": value}
    return {
        "ok": True,
        "patch": {
            "jog": {
                "armRequired": bool(form.get("armRequired", False)),
                "armTtlMs": ttl_ms,
                "default": {"maxAmount": amount, "maxAbsolute": absolute},
                "models": jog_models,
            },
            "temperature": {"default": {"bedMaxC": bed}, "models": temp_models},
            "claims": {"requireControllerId": bool(form.get("requireControllerId", False))},
        },
    }


def form_from_limits(limits: SafetyLimits) -> dict:
    """The form values that show what the server holds (numbers as text, one row per model)."""

    def show(value: float | None) -> str:
        if value is None:
            return ""
        return str(int(value)) if float(value).is_integer() else str(value)

    keys = sorted({*limits.jog_models, *limits.bed_models})
    return {
        "armRequired": limits.arm_required,
        "armTtlSeconds": show(round(limits.arm_ttl_ms / 1000)),
        "requireControllerId": limits.require_controller_id,
        "defaultMaxAmount": show(limits.jog_default_amount),
        "defaultMaxAbsolute": show(limits.jog_default_absolute),
        "defaultBedMaxC": show(limits.bed_default_c),
        "rows": [
            {
                "model": key,
                "maxAmount": show(limits.jog_models.get(key, {}).get("maxAmount")),
                "maxAbsolute": show(limits.jog_models.get(key, {}).get("maxAbsolute")),
                "bedMaxC": show(limits.bed_models.get(key)),
            }
            for key in keys
        ],
    }


# --- the warnings of the server --------------------------------------------------------------------------------


@dataclass
class ServerWarning:
    code: str | None = None
    field: str | None = None
    message: str | None = None
    requested: float | None = None
    applied: float | None = None
    robot_id: int | None = None

    @property
    def is_jog(self) -> bool:
        return self.field == "jog"

    @property
    def is_temperature(self) -> bool:
        return self.code == "temperature-limit"


def parse_warnings(body: object) -> list[ServerWarning]:
    """The structured warnings of an answer (objects with a code, a field or a message; plain strings become a
    message)."""
    listed = body.get("warnings") if isinstance(body, dict) else None
    if not isinstance(listed, list):
        return []
    out: list[ServerWarning] = []
    for item in listed:
        if isinstance(item, str):
            out.append(ServerWarning(message=item))
        elif isinstance(item, dict):

            def number(value: object) -> float | None:
                return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

            robot_id = item.get("robotId")
            out.append(
                ServerWarning(
                    code=item["code"] if isinstance(item.get("code"), str) else None,
                    field=item["field"] if isinstance(item.get("field"), str) else None,
                    message=item["message"] if isinstance(item.get("message"), str) else None,
                    requested=number(item.get("requested")),
                    applied=number(item.get("applied")),
                    robot_id=int(robot_id) if isinstance(robot_id, (int, float)) and not isinstance(robot_id, bool) else None,
                )
            )
        else:
            out.append(ServerWarning())
    return out


# --- Live or Sim -------------------------------------------------------------------------------------------------

#: The commands that move a robot or switch something on: refused while the robot is in Sim.
REAL_COMMANDS = frozenset({"jog", "table", "play", "reset", "tool", "valve", "pump", "trajectory", "speed"})


def is_real_command(command: str) -> bool:
    return command in REAL_COMMANDS


def mode_key(scope: str, robot_id: int) -> str:
    """Robot ids repeat from one server to the next, so a choice is filed under the server and the robot."""
    return f"{scope}#{robot_id}"


@dataclass
class ModeState:
    """The Live or Sim choice of each robot (of each server), and the mode of a robot with no explicit choice
    (Live by default)."""

    modes: dict[str, str] = field(default_factory=dict)
    default_mode: str = "live"

    def mode_of(self, scope: str, robot_id: int) -> str:
        return self.modes.get(mode_key(scope, robot_id), self.default_mode)

    def blocked(self, scope: str, robot_ids: list[int], command: str) -> bool:
        """Whether a command is refused: a real command while any of the robots is in Sim."""
        return is_real_command(command) and any(self.mode_of(scope, r) == "sim" for r in robot_ids)

    def set_mode(self, scope: str, robot_id: int, mode: str) -> None:
        if mode in ("live", "sim"):
            self.modes[mode_key(scope, robot_id)] = mode

    def set_default(self, mode: str) -> None:
        if mode in ("live", "sim"):
            self.default_mode = mode

    def to_config(self) -> dict:
        return {"robotModes": dict(self.modes), "defaultRobotMode": self.default_mode}

    @classmethod
    def from_config(cls, config: object) -> "ModeState":
        state = cls()
        if not isinstance(config, dict):
            return state
        if config.get("defaultRobotMode") == "sim":
            state.default_mode = "sim"
        raw = config.get("robotModes")
        if isinstance(raw, dict):
            for key, value in raw.items():
                if isinstance(key, str) and "#" in key and value in ("live", "sim"):
                    state.modes[key] = value
        return state


#: The Live or Sim choices of this program (one for all servers), loaded from the configuration at start.
MODES = ModeState()


# --- conditional writes (contract v2, block 2) ---------------------------------------------------------------
#
# The server gives every robot a revision (GET /api/robot/:id, and every answer of a command, a reservation or a
# release carries the new one). A write that sends it back as If-Match is refused with 412 when the robot changed
# in between, so this program never overwrites what someone else did to the robot without knowing it. The tracker
# keeps the last revision seen for each robot of one server and decides when it is sent:
#   - never when none is known (the first write learns it), when another write to the same robot is still on its
#     way (its answer is what makes the revision stale, not a change by someone else), or after this program
#     saved the whole settings tree (that save changes the robot too);
#   - never for STOP, which is never conditional;
#   - by the mode chosen in this program: off, standard (reservations, the table and the discrete commands; the
#     continuous ones - jog and speed - go unconditional) or strict (everything but STOP). The default is standard.

CONDITIONAL_MODES = ("off", "standard", "strict")
DEFAULT_CONDITIONAL_MODE = "standard"
#: Commands sent many times a second while a control is held: a revision can not follow them.
CONTINUOUS_COMMANDS = frozenset({"jog", "speed", "jogStep"})

_REVISION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def is_conditional(mode: str, command: str) -> bool:
    """Whether a command carries If-Match in a mode. Reservations are "claim" and "release". STOP never does."""
    if command == "stop" or mode == "off":
        return False
    if mode == "strict":
        return True
    return command not in CONTINUOUS_COMMANDS


def revision_of(body: object) -> str | None:
    """The revision in the body of an answer (`revision`), or None."""
    value = body.get("revision") if isinstance(body, dict) else None
    return value if isinstance(value, str) and _REVISION_PATTERN.fullmatch(value) else None


def if_match_header(revision: str) -> str:
    """The value of the If-Match header for a revision (quoted, as an ETag is)."""
    return f'"{revision}"'


@dataclass
class ConditionalSetting:
    """The mode of this program, one for every server (kept in the configuration)."""

    mode: str = DEFAULT_CONDITIONAL_MODE

    def set(self, mode: str) -> None:
        if mode in CONDITIONAL_MODES:
            self.mode = mode

    def to_config(self) -> dict:
        return {"conditionalWrites": self.mode}

    @classmethod
    def from_config(cls, config: object) -> "ConditionalSetting":
        value = config.get("conditionalWrites") if isinstance(config, dict) else None
        return cls(value if value in CONDITIONAL_MODES else DEFAULT_CONDITIONAL_MODE)


#: The mode of this program, loaded from the configuration at start.
CONDITIONAL = ConditionalSetting()


@dataclass
class RevisionTicket:
    if_match: str | None
    seq: int


class RevisionTracker:
    """The last revision seen of each robot of one server. `begin` before a write, `finish` when it was answered."""

    def __init__(self, setting: ConditionalSetting | None = None) -> None:
        self._setting = setting if setting is not None else CONDITIONAL
        self._counter = 0
        self._known: dict[str, tuple[str, int]] = {}
        self._in_flight: dict[str, int] = {}

    def begin(self, robot_id: int | str, command: str) -> RevisionTicket:
        """The If-Match value for a write to a robot (None when none must be sent). Counts the write as on its way."""
        robot_id = str(robot_id)
        self._counter += 1
        seq = self._counter
        busy = self._in_flight.get(robot_id, 0) > 0
        self._in_flight[robot_id] = self._in_flight.get(robot_id, 0) + 1
        entry = self._known.get(robot_id)
        if not busy and entry is not None and is_conditional(self._setting.mode, command):
            return RevisionTicket(if_match_header(entry[0]), seq)
        return RevisionTicket(None, seq)

    def finish(self, robot_id: int | str, seq: int, revision: str | None) -> None:
        """The write was answered: keep the revision it carried (when it is the newest answer) and stop counting it."""
        robot_id = str(robot_id)
        left = self._in_flight.get(robot_id, 1) - 1
        if left <= 0:
            self._in_flight.pop(robot_id, None)
        else:
            self._in_flight[robot_id] = left
        if revision is None:
            # An answer without a revision (a refusal, an older server): what was known may be stale now.
            if left <= 0:
                self._known.pop(robot_id, None)
            return
        entry = self._known.get(robot_id)
        if entry is None or seq >= entry[1]:
            self._known[robot_id] = (revision, seq)

    def learn(self, robot_id: int | str, revision: str | None) -> None:
        """A revision learned some other way (the 412 answer, GET /api/robot/:id)."""
        robot_id = str(robot_id)
        if revision is None:
            self._known.pop(robot_id, None)
            return
        self._counter += 1
        self._known[robot_id] = (revision, self._counter)

    def forget(self, robot_id: int | str | None = None) -> None:
        """Forgets what was known (the whole tree was saved from this program)."""
        if robot_id is None:
            self._known.clear()
        else:
            self._known.pop(str(robot_id), None)

    def known(self, robot_id: int | str) -> str | None:
        entry = self._known.get(str(robot_id))
        return entry[0] if entry is not None else None


# --- the atomic move of the XY table (contract v2, block 3) ------------------------------------------------------
#
# The "table" command of the server moves the XY table of one robot in one request ({x, y, rz?, mode}) instead of
# one jog per axis: the server checks the whole move against the jog limits of the model and applies all of it or
# none of it. These helpers build and check that request here (the server checks again) and, for a server that
# predates the command, turn it into the jogs that did the same before.


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value not in (float("inf"), float("-inf"))


def table_params(x: object, y: object, mode: str, rz: object = None) -> dict | None:
    """The parameters of a table move, or None when they are not numbers."""
    if not _finite(x) or not _finite(y) or (rz is not None and not _finite(rz)) or mode not in ("absolute", "relative"):
        return None
    params: dict = {"x": x, "y": y, "mode": mode}
    if rz is not None:
        params["rz"] = rz
    return params


def check_table(limits: SafetyLimits, model: object, params: dict | None, current: dict | None = None) -> JogCheck:
    """Whether a table move is inside the limits of the model before it is sent: every number of a relative move
    within the largest jog, every number of an absolute move (and the position a relative one ends in) within the
    largest absolute position."""
    max_amount, max_absolute = jog_limits_for(limits, model)
    params = params or {}
    relative = params.get("mode") == "relative"
    requested = [(axis, params.get(axis)) for axis in ("x", "y", "rz") if params.get(axis) is not None]
    limit = max_amount if relative else max_absolute
    for _axis, value in requested:
        if _finite(value) and abs(value) > limit:
            return JogCheck(False, limit, "amount" if relative else "absolute")
    if relative and current:
        for axis, value in requested:
            if _finite(value):
                base = current.get(axis)
                base = float(base) if _finite(base) else 0.0
                if abs(base + value) > max_absolute:
                    return JogCheck(False, max_absolute, "absolute")
    return JogCheck(True, limit, None)


def is_unknown_command(status: int, server_code: str | None, detail: str | None) -> bool:
    """An older server answers 400 "unknown command" to a command it does not have."""
    return status == 400 and server_code is None and "unknown command" in (detail or "").lower()


def table_as_jogs(params: dict) -> list[dict]:
    """The jogs that did the same on a server without the table command (one per axis that moves; no rotation)."""
    absolute = params.get("mode") != "relative"
    jogs: list[dict] = []
    for axis in ("x", "y"):
        amount = params.get(axis)
        if not _finite(amount):
            continue
        if not absolute and amount == 0:
            continue
        jog = {"axis": axis, "amount": amount, "target": "xytable"}
        if absolute:
            jog["absolute"] = True
        jogs.append(jog)
    return jogs


# --- the audit record (contract v2, block 4) -----------------------------------------------------------------------
#
# GET /api/audit (administrators only) gives the newest entries of an append-only log: every line carries the SHA-256
# of the line before it (`prev`) and its own (`hash`), so a line that is changed or removed later shows when the
# chain is checked. The server can check the whole record (?verify=1); this program can also check what it was
# given: every hash is computed again here and every line that follows its predecessor directly must name it.

AUDIT_TYPES = ("claim", "force-claim", "release", "force-release", "jog-arm", "safety-limits", "stop-all")


@dataclass
class AuditEntry:
    seq: int
    ts: str
    type: str
    outcome: str
    username: str | None
    controller_id: str | None
    ip: str | None
    robot_id: int | None
    detail: dict | None
    prev: str
    hash: str
    # The line as the server sent it, without the hash: what the hash is the SHA-256 of.
    raw: dict = field(default_factory=dict)


@dataclass
class AuditRead:
    enabled: bool = True
    locked_off: bool = False
    entries: list[AuditEntry] = field(default_factory=list)
    # The verification of the server over the whole record ({"ok", "entries", "brokenAtSeq", "reason"}), if asked.
    verification: dict | None = None


def _parse_audit_entry(value: object) -> AuditEntry | None:
    if not isinstance(value, dict):
        return None
    seq, ts, kind, prev, digest = value.get("seq"), value.get("ts"), value.get("type"), value.get("prev"), value.get("hash")
    if isinstance(seq, bool) or not isinstance(seq, int) or not isinstance(ts, str) or not isinstance(kind, str):
        return None
    if not isinstance(prev, str) or not isinstance(digest, str):
        return None
    robot_id = value.get("robotId")
    outcome = value.get("outcome")
    return AuditEntry(
        seq=seq,
        ts=ts,
        type=kind,
        outcome=outcome if outcome in ("refused", "failed") else "ok",
        username=_text(value.get("username")),
        controller_id=_text(value.get("controllerId")),
        ip=_text(value.get("ip")),
        robot_id=int(robot_id) if isinstance(robot_id, (int, float)) and not isinstance(robot_id, bool) else None,
        detail=value["detail"] if isinstance(value.get("detail"), dict) else None,
        prev=prev,
        hash=digest,
        raw={k: v for k, v in value.items() if k != "hash"},
    )


def parse_audit(body: object) -> AuditRead:
    """The answer of GET /api/audit; lines that are not entries are dropped."""
    if not isinstance(body, dict):
        return AuditRead()
    listed = body.get("entries") if isinstance(body.get("entries"), list) else []
    entries = [entry for entry in (_parse_audit_entry(item) for item in listed) if entry is not None]
    verification = body.get("verification") if isinstance(body.get("verification"), dict) else None
    return AuditRead(
        enabled=body.get("enabled") is not False,
        locked_off=body.get("lockedOff") is True,
        entries=entries,
        verification=verification,
    )


@dataclass(frozen=True)
class ChainCheck:
    #: Every hash matched and every line that follows directly names its predecessor.
    ok: bool
    checked: int
    #: Links between neighbours that could be compared (a filter or a rotated file leaves gaps that can not).
    links: int
    gaps: int
    broken_at_seq: int | None = None
    reason: str | None = None  # "changed" | "link"


def hash_of_line(raw: dict) -> str:
    """The SHA-256 the server wrote for a line: of the line without `hash`, as compact JSON in the order it was written."""
    import hashlib
    import json

    return hashlib.sha256(json.dumps(raw, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def check_chain(entries: list[AuditEntry]) -> ChainCheck:
    """Checks the hash of every line and the link between lines that are neighbours (sequence numbers one apart)."""
    links = 0
    gaps = 0
    for index, entry in enumerate(entries):
        if hash_of_line(entry.raw) != entry.hash:
            return ChainCheck(False, index, links, gaps, entry.seq, "changed")
        if index == 0:
            continue
        before = entries[index - 1]
        if entry.seq == before.seq + 1:
            links += 1
            if entry.prev != before.hash:
                return ChainCheck(False, index + 1, links, gaps, entry.seq, "link")
        else:
            gaps += 1
    return ChainCheck(True, len(entries), links, gaps)


def detail_line(detail: dict | None, maximum: int = 140) -> str:
    """A short line of the detail of an entry for the table: key=value pairs, bounded."""
    if not detail:
        return ""
    import json

    parts = [f"{k}={json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}" for k, v in detail.items()]
    joined = " ".join(parts)
    return joined if len(joined) <= maximum else joined[: maximum - 3] + "..."


def audit_query(limit: int | None = None, type: str | None = None, robot_id: int | None = None, verify: bool = False) -> str:
    """The query string of GET /api/audit for a filter (limit 1 to 1000)."""
    from urllib.parse import urlencode

    pairs: list[tuple[str, str]] = []
    if limit is not None:
        pairs.append(("limit", str(min(1000, max(1, int(limit))))))
    if type:
        pairs.append(("type", type))
    if robot_id is not None:
        pairs.append(("robotId", str(int(robot_id))))
    if verify:
        pairs.append(("verify", "1"))
    return "?" + urlencode(pairs) if pairs else ""
