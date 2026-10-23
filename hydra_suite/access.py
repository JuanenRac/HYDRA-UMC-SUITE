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
    "claim_other_account", "claim_other_controller", "claim_controller_required", "jog_not_armed", or the plain
    class of the status ("network", "session_expired", "forbidden", "not_found", "claimed", "rejected", "server")."""
    if server_code == "other-account":
        return "claim_other_account"
    if server_code == "other-controller":
        return "claim_other_controller"
    if server_code == "controller-id-required":
        return "claim_controller_required"
    if server_code == "jog-not-armed":
        return "jog_not_armed"
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
REAL_COMMANDS = frozenset({"jog", "play", "reset", "tool", "valve", "pump", "trajectory", "speed"})


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
