# =============================================================================
# HYDRA-UMC SUITE - tests/verify_access.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The rules of hydra_suite/access.py and hydra_suite/joint_limits.py, with no Qt and no network:
#   - the controller id of this program is valid, stable and what the server accepts
#   - the reservations of GET /api/claims, and where a robot stands for this program
#   - the refusals of the server told apart by their code
#   - the safety limits read from the server (per model, hard ceilings, damaged answers), the jog checked before
#     it is sent, the bed ceiling, the form of the administration screen and the request it builds
#   - the warnings of the server (a jog not applied, a bed target lowered)
#   - Live or Sim: what Sim blocks, what it lets through, and how the choice is kept
#   - the range of every joint of the models that have one
# =============================================================================
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydra_suite import access
from hydra_suite.joint_limits import GENERIC_RANGE_DEG, JOINT_LIMITS_DEG, clamp_joint, joint_range_deg

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


def controller_id():
    check("id: the server's pattern", [access.is_valid_controller_id(v) for v in ("suite-ab12", "a.b_c:d-e", "x" * 64, "x" * 65, "", "has space", "semi;colon", 7)], [True, True, True, False, False, False, False, False])
    generated = access.generate_controller_id(random.Random(1))
    check("id: a generated id is valid and starts with suite-", (access.is_valid_controller_id(generated), generated.startswith("suite-")), (True, True))
    check("id: two generated ids differ", access.generate_controller_id() != access.generate_controller_id(), True)
    access.reset_controller_id()
    first = access.get_controller_id()
    check("id: chosen once and kept", access.get_controller_id(), first)
    access.reset_controller_id("not valid!")
    check("id: a damaged id is replaced", access.is_valid_controller_id(access.get_controller_id()), True)
    access.reset_controller_id()


def claims():
    now = time.time() * 1000
    parsed = access.parse_claims({"claims": [
        {"robotId": 3, "robotName": "Arm 3", "cellId": "c", "ownerId": "u", "ownerUsername": "ana", "controllerId": "w", "claimedAt": now, "expiresAt": now + 60000},
        {"robotId": "x"}, None, 7, {"robotId": 4, "ownerUsername": "", "controllerId": None}, {"robotId": True},
    ]})
    check("claims: only objects with a robot id are kept", [c.robot_id for c in parsed], [3, 4])
    check("claims: the owner and controller are read", (parsed[0].owner_username, parsed[0].controller_id), ("ana", "w"))
    check("claims: a missing owner reads as ?", (parsed[1].owner_username, parsed[1].controller_id), ("?", None))
    check("claims: seconds left", parsed[0].seconds_left(now) in (59, 60), True)
    check("claims: never negative", access.ClaimEntry(1, expires_at=now - 5000).seconds_left(now), 0)
    check("claims: no expiry", access.ClaimEntry(1).seconds_left(now), None)
    check("claims: nothing or garbage", (access.parse_claims(None), access.parse_claims({"claims": "x"})), ([], []))
    iso = access.parse_claims({"claims": [{"robotId": 1, "expiresAt": "2030-01-01T00:00:00.000Z"}]})
    check("claims: an ISO date", iso[0].expires_at, 1893456000000.0)

    here = "suite-here"
    held = access.ClaimEntry(1, owner_username="ana", controller_id=here)
    check("standing: free", access.claim_standing(None, here, "ana"), "free")
    check("standing: mine", access.claim_standing(held, here, "ana"), "mine")
    check("standing: same account, another controller", access.claim_standing(held, "suite-other", "ana"), "other-controller")
    check("standing: another account", access.claim_standing(held, "suite-other", "bob"), "other-account")
    check("standing: no controller on the claim, same account", access.claim_standing(access.ClaimEntry(1, owner_username="ana"), here, "ana"), "mine")
    check("standing: no controller on the claim, another account", access.claim_standing(access.ClaimEntry(1, owner_username="ana"), here, "bob"), "other-account")
    check("standing: unknown account is never mine", access.claim_standing(held, "suite-other", None), "other-account")


def refusals():
    for code, expected in (("other-account", "claim_other_account"), ("other-controller", "claim_other_controller"), ("controller-id-required", "claim_controller_required"), ("jog-not-armed", "jog_not_armed")):
        check(f"refusal: {code}", access.failure_code_for(409 if code != "jog-not-armed" else 403, code), expected)
    check("refusal: a 409 without a code stays generic", access.failure_code_for(409, None), "claimed")
    check("refusal: the other statuses", [access.failure_code_for(s, None) for s in (0, 401, 403, 404, 400, 500)], ["network", "session_expired", "forbidden", "not_found", "rejected", "server"])
    check("refusal: code of a body", (access.conflict_code_of({"code": "other-controller"}), access.conflict_code_of({"code": "x"}), access.conflict_code_of("t")), ("other-controller", None, None))


def limits():
    state = access.parse_safety_limits(None)
    check("limits: conservative defaults before the server answers", (state.limits.arm_required, state.limits.jog_default_amount, state.limits.jog_default_absolute, state.limits.bed_default_c, state.limits.require_controller_id), (False, 100, 1000, 110, False))
    check("limits: and the hard ceilings of the server", (state.hard.jog_max_amount, state.hard.jog_max_absolute, state.hard.bed_max_c), (1000, 10000, 300))
    state = access.parse_safety_limits({
        "limits": {
            "jog": {"armRequired": True, "armTtlMs": 30000, "default": {"maxAmount": 50, "maxAbsolute": 800}, "models": {"Parol6 (6-DOF)": {"maxAmount": 10}, "AR4 (6-DOF)": {"maxAbsolute": 500}}},
            "temperature": {"default": {"bedMaxC": 100}, "models": {"AR4 (6-DOF)": {"bedMaxC": 90}}},
            "claims": {"requireControllerId": True},
        },
        "hardLimits": {"jogMaxAmount": 900, "jogMaxAbsolute": 9000, "armTtlMs": {"min": 2000, "max": 500000}, "bedMaxC": 250},
    })
    check("limits: read from the server", (state.limits.arm_required, state.limits.arm_ttl_ms, state.limits.require_controller_id, state.hard.bed_max_c), (True, 30000, True, 250))
    check("limits: a model's own value over the default", (access.jog_limits_for(state.limits, "Parol6 (6-DOF)"), access.jog_limits_for(state.limits, "AR4 (6-DOF)"), access.jog_limits_for(state.limits, "Z1 (6-DOF)")), ((10, 800), (50, 500), (50, 800)))
    check("limits: the bed ceiling by model", (access.bed_max_for(state.limits, "AR4 (6-DOF)"), access.bed_max_for(state.limits, "Z1 (6-DOF)"), access.highest_bed_max(state.limits)), (90, 100, 100))
    damaged = access.parse_safety_limits({"limits": {"jog": {"armRequired": "yes", "armTtlMs": -5, "default": {"maxAmount": "big", "maxAbsolute": 0}, "models": {"x": "no", "y": {"maxAmount": -1}}}}})
    check("limits: damaged values keep the defaults", (damaged.limits.arm_required, damaged.limits.arm_ttl_ms, damaged.limits.jog_default_amount, damaged.limits.jog_default_absolute, damaged.limits.jog_models), (False, 60000, 100, 1000, {"y": {}}))
    check("limits: the model key", (access.model_key("Parol6 (6-DOF)"), access.model_key("  UR5e "), access.model_key(None)), ("parol6", "ur5e", ""))


def jog():
    limits = access.parse_safety_limits({"limits": {"jog": {"default": {"maxAmount": 100, "maxAbsolute": 1000}, "models": {"parol6": {"maxAmount": 20}, "ar4": {"maxAbsolute": 500}}}}}).limits
    check("jog: inside the limit", access.check_jog(limits, "Parol6 (6-DOF)", {"axis": "x", "amount": 20}), access.JogCheck(True, 20, None))
    check("jog: over it, either direction", [access.check_jog(limits, "Parol6 (6-DOF)", {"axis": "x", "amount": a}).ok for a in (21, -21)], [False, False])
    check("jog: says which limit", access.check_jog(limits, "Parol6 (6-DOF)", {"axis": "x", "amount": 21}), access.JogCheck(False, 20, "amount"))
    check("jog: the default for a model with no entry", [access.check_jog(limits, "Z1 (6-DOF)", {"amount": a}).ok for a in (100, 101)], [True, False])
    check("jog: an absolute jog is bounded by the position", [access.check_jog(limits, "AR4 (6-DOF)", {"absolute": True, "amount": a}).ok for a in (500, -500, 501, -501)], [True, True, False, False])
    check("jog: a pure joint move (amount 0) goes through", (access.check_jog(limits, "Parol6 (6-DOF)", {"axis": "x", "amount": 0}).ok, access.check_jog(limits, "Parol6 (6-DOF)", None).ok), (True, True))
    check("bed: clamped to the ceiling", [access.clamp_bed_target(v, 110) for v in (0, 300, -5, 60.4, float("nan"), "hot", True)], [0, 110, 0, 60, 0, 0, 0])
    check("arming: still running or not", [access.is_armed(v, 1000) for v in (2000, 1000, None, "x")], [True, False, False, False])


def form():
    state = access.parse_safety_limits({"limits": {"jog": {"models": {"parol6": {"maxAmount": 20}, "ar4": {"maxAbsolute": 500}}}, "temperature": {"models": {"parol6": {"bedMaxC": 80}}}}})
    values = access.form_from_limits(state.limits)
    check("form: one row per model", [r["model"] for r in values["rows"]], ["ar4", "parol6"])
    check("form: seconds, not milliseconds", values["armTtlSeconds"], "60")
    built = access.build_patch(values, state.hard)
    check("form: the request the server accepts", built["patch"], {
        "jog": {"armRequired": False, "armTtlMs": 60000, "default": {"maxAmount": 100.0, "maxAbsolute": 1000.0}, "models": {"ar4": {"maxAbsolute": 500.0}, "parol6": {"maxAmount": 20.0}}},
        "temperature": {"default": {"bedMaxC": 110.0}, "models": {"parol6": {"bedMaxC": 80.0}}},
        "claims": {"requireControllerId": False},
    })
    switched = dict(values, armRequired=True, requireControllerId=True, armTtlSeconds="30")
    patch = access.build_patch(switched, state.hard)["patch"]
    check("form: the switches and the seconds", (patch["jog"]["armRequired"], patch["jog"]["armTtlMs"], patch["claims"]["requireControllerId"]), (True, 30000, True))
    for label, change, problem, field in (
        ("over the jog ceiling", {"defaultMaxAmount": "1001"}, "range", "defaultMaxAmount"),
        ("over the absolute ceiling", {"defaultMaxAbsolute": "10001"}, "range", "defaultMaxAbsolute"),
        ("over the bed ceiling", {"defaultBedMaxC": "301"}, "range", "defaultBedMaxC"),
        ("not a number", {"defaultBedMaxC": "hot"}, "number", "defaultBedMaxC"),
        ("zero", {"defaultMaxAmount": "0"}, "range", "defaultMaxAmount"),
        ("arming too short", {"armTtlSeconds": "0.5"}, "range", "armTtl"),
        ("arming too long", {"armTtlSeconds": "601"}, "range", "armTtl"),
        ("arming empty", {"armTtlSeconds": ""}, "number", "armTtl"),
    ):
        result = access.build_patch(dict(values, **change), state.hard)
        check(f"form: refused, {label}", (result["ok"], result["problem"], result["field"]), (False, problem, field))
    rows = lambda *r: dict(values, rows=list(r))
    row = lambda **kw: dict({"model": "ur5e", "maxAmount": "", "maxAbsolute": "", "bedMaxC": ""}, **kw)
    check("form: a row over its ceiling", access.build_patch(rows(row(maxAmount="5000")), state.hard)["field"], "ur5e.maxAmount")
    check("form: a row with no model", access.build_patch(rows(row(model="  ")), state.hard)["problem"], "model")
    check("form: the same model twice", access.build_patch(rows(row(model="UR5e (6-DOF)"), row()), state.hard)["problem"], "duplicate")
    ok = access.build_patch(rows(row(model="UR5e (6-DOF)", bedMaxC="90"), row(model="z1")), state.hard)["patch"]
    check("form: an empty row adds nothing, a bed value goes to the temperature table", (ok["jog"]["models"], ok["temperature"]["models"]), ({}, {"ur5e": {"bedMaxC": 90.0}}))


def warnings():
    parsed = access.parse_warnings({"warnings": [
        {"robotId": 1, "field": "jog", "requested": "x", "message": "jog needs a valid axis"},
        {"robotId": 2, "field": "heatedBed.targetTemp", "requested": 300, "applied": 110, "code": "temperature-limit"},
        "plain text", 7,
    ]})
    check("warnings: a jog and a lowered target", (parsed[0].is_jog, parsed[1].is_temperature, parsed[1].requested, parsed[1].applied, parsed[1].robot_id), (True, True, 300.0, 110.0, 2))
    check("warnings: plain strings are messages", parsed[2].message, "plain text")
    check("warnings: nothing or garbage", (access.parse_warnings(None), access.parse_warnings({"warnings": "x"})), ([], []))


def live_sim():
    state = access.ModeState()
    check("sim: Live by default", state.mode_of("s", 1), "live")
    check("sim: Live blocks nothing", state.blocked("s", [1], "jog"), False)
    state.set_mode("s", 1, "sim")
    check("sim: blocks what moves a robot or switches something on", [state.blocked("s", [1], c) for c in ("jog", "play", "reset", "tool", "valve", "pump")], [True] * 6)
    check("sim: lets the harmless through, and STOP always", [state.blocked("s", [1], c) for c in ("stop", "pause", "jogStep", "speed", "trajectory", "vision", "reset3D")], [False] * 7)
    check("sim: only that robot, on that server", (state.blocked("s", [2], "jog"), state.blocked("other", [1], "jog")), (False, False))
    check("sim: a group when any robot is", state.blocked("s", [2, 1], "play"), True)
    state.set_default("sim")
    state.set_mode("s", 3, "live")
    check("sim: a browser can start in Sim, an explicit choice wins", (state.mode_of("s", 5), state.mode_of("s", 3)), ("sim", "live"))
    state.set_mode("s", 4, "fast")
    check("sim: an unknown mode is ignored", state.mode_of("s", 4), "sim")
    restored = access.ModeState.from_config(state.to_config())
    check("sim: kept and restored", (restored.modes, restored.default_mode), (state.modes, "sim"))
    check("sim: damaged configuration", (access.ModeState.from_config(None).modes, access.ModeState.from_config({"robotModes": {"x": "sim", "s#1": "fast", "s#2": "sim"}}).modes), ({}, {"s#2": "sim"}))


def joints():
    check("joints: a model with a published range", joint_range_deg("Parol6 (6-DOF)", "j1"), (-97.4, 187.4))
    check("joints: another", joint_range_deg("UR3e (6-DOF)", "j3"), (-180.0, 180.0))
    check("joints: a model without one gets the generic range", (joint_range_deg("Z1 (6-DOF)", "j1"), joint_range_deg(None, "j2")), (GENERIC_RANGE_DEG, GENERIC_RANGE_DEG))
    check("joints: twelve models have a table of six joints", (len(JOINT_LIMITS_DEG), {len(v) for v in JOINT_LIMITS_DEG.values()}), (12, {6}))
    check("joints: clamped to the range", (clamp_joint("Parol6 (6-DOF)", "j1", 500), clamp_joint("Parol6 (6-DOF)", "j1", -500), clamp_joint("Parol6 (6-DOF)", "j1", 10)), (187.4, -97.4, 10))
    check("joints: every range is ordered", all(low < high for table in JOINT_LIMITS_DEG.values() for low, high in table.values()), True)


def main():
    controller_id()
    claims()
    refusals()
    limits()
    jog()
    form()
    warnings()
    live_sim()
    joints()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
