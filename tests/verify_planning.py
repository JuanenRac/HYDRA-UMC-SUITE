# =============================================================================
# HYDRA-UMC SUITE - tests/verify_planning.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Verifies the Planning and operation screen without any window: how a plan is read, what the dry run answers (and what it refuses to show),
# the estimates of the job dispatcher, the remaining useful life, a version train read from `train plan --json`, the switch of the window
# statistics of the data lake, and that the screen can only make the few requests it is meant to make.
# =============================================================================
import asyncio
import json
import sys

sys.path.insert(0, ".")

from hydra_suite.i18n import _
from hydra_suite.panel_logic import planning

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


ACCEPTED = {
    "verdict": "accepted", "executable": False, "executed": False, "violations": [],
    "timeline": [{"step_id": "a", "index": 0, "robot": "r1", "primitive": "MOVE_TO", "start_ms": 0, "end_ms": 1000}], "makespan_ms": 1000,
}

# -- the dry run
check("a request is an object with a non-empty list of steps",
      [planning.parse_plan_request(x) is not None for x in ('{"steps":[{"primitive":"WAIT"}]}', "", "{", "[]", '{"steps":[]}', '{"steps":"x"}', '{"constraints":{}}', "null")],
      [True, False, False, False, False, False, False, False])
check("a deeply nested text is refused, not a crash", planning.parse_plan_request("[" * 100000), None)
sim = planning.parse_simulation({**ACCEPTED, "verdict": "rejected", "violations": [{"rule": "workspace_limit", "step_id": "b", "message": "out", "suggestion": {"x": 1}}, {"nope": 1}]})
check("reads the violations and drops a damaged one", sim["violations"], [{"rule": "workspace_limit", "stepId": "b", "message": "out", "suggestion": '{"x":1}'}])
check("reads the timeline", planning.parse_simulation(ACCEPTED)["timeline"], [{"stepId": "a", "robot": "r1", "primitive": "MOVE_TO", "startMs": 0, "endMs": 1000}])
check("never shows an answer that claims to have executed, to be executable, an unknown verdict or an accepted plan with a violation",
      [planning.parse_simulation(x) for x in ({**ACCEPTED, "executed": True}, {**ACCEPTED, "executable": True}, {**ACCEPTED, "executable": None}, {**ACCEPTED, "verdict": "maybe"},
                                              {**ACCEPTED, "violations": [{"rule": "x", "message": ""}]}, "x", None)],
      [None] * 7)
view = planning.simulation_view(sim)
check("the view of a rejected plan", (view["accepted"], view["verdictText"], view["violations"], view["notExecuted"]),
      (False, _("PLANNING_SIM_REJECTED"), ['workspace_limit (b): out - {"x":1}'], _("PLANNING_SIM_NOT_EXECUTED")))
check("the view of an accepted plan", (planning.simulation_view(planning.parse_simulation(ACCEPTED))["accepted"], planning.simulation_view(planning.parse_simulation(ACCEPTED))["makespan"]),
      (True, f"{_('PLANNING_SIM_MAKESPAN')}: 1 s"))

# -- why it could not answer
check("the sentences for an answer that is not a 200",
      [planning.failure_text(*x) for x in ((200,), (404,), (403,), (401,), (503,), (500,), (None,), (400, {"error": "steps must be a list"}), (400, None))],
      ["", _("PLANNING_OFF"), _("PLANNING_FORBIDDEN"), _("PLANNING_FORBIDDEN"), _("PLANNING_UNREACHABLE"), _("PLANNING_HTTP"), _("PLANNING_NETWORK"),
       _("PLANNING_INVALID") + "steps must be a list", _("PLANNING_HTTP")])

# -- the estimates of the dispatcher
ETA = {
    "generatedAtMs": 1_760_000_000_000, "drainMs": 1_760_000_180_000,
    "jobs": [
        {"jobId": "weld-42", "status": "assigned", "estimated": True, "robotId": "arm-3", "startMs": 1, "endMs": 1_760_000_061_000, "durationMs": 61000, "endLowMs": 1_760_000_050_000, "endHighMs": 1_760_000_080_000},
        {"jobId": "weld-44", "status": "pending", "estimated": False, "reason": "no_robot_with_required_tool"},
        {"status": "pending"},
    ],
}
eta = planning.parse_eta(ETA)
check("reads the jobs and drops a damaged row", [j["jobId"] for j in eta["jobs"]], ["weld-42", "weld-44"])
check("the rows of the estimates", planning.eta_view(eta)["rows"],
      ["weld-42  assigned  arm-3  1 min 1 s [50 s - 1 min 20 s]", f"weld-44  pending  -  {_('PLANNING_ETA_NO_ESTIMATE')} (no_robot_with_required_tool)"])
check("the queue drains", planning.eta_view(eta)["drain"], f"{_('PLANNING_ETA_DRAIN')} 3 min 0 s")
check("an answer that is not the estimates", (planning.parse_eta({"jobs": []}), planning.parse_eta(None), planning.eta_view(planning.parse_eta({"generatedAtMs": 1, "jobs": []}))["empty"]), (None, None, _("PLANNING_ETA_EMPTY")))
check("a duration", [planning.format_duration(x) for x in (5000, 200000, 7_260_000, None, -1, float("nan"), True)], ["5 s", "3 min 20 s", "2 h 1 min", "-", "-", "-", "-"])

# -- the remaining useful life
check("reads points one per line", planning.parse_rul_points("0, 0.1\n86400 0.2;\n172800\t0.4\n\n"), [{"t": 0.0, "score": 0.1}, {"t": 86400.0, "score": 0.2}, {"t": 172800.0, "score": 0.4}])
check("a wrong point is refused", [planning.parse_rul_points(x) for x in ("", "1", "1,2,3", "a,b", "1,nan", "1,inf")], [None] * 6)
check("at most 1000 points", (planning.parse_rul_points("\n".join(f"{i},1" for i in range(1001))), len(planning.parse_rul_points("\n".join(f"{i},1" for i in range(1000))))), (None, 1000))
check("the limit is a number", [planning.parse_limit(x) for x in ("5", "5,5", "", "x", "inf")], [5.0, 5.5, None, None, None])
estimate = planning.parse_rul({"status": "estimated", "points": 10, "slopePerDay": 0.1, "currentValue": 0.5, "daysToLimit": 12.5, "daysLow": 8, "daysHigh": None})
check("reads an estimate and shows its range", planning.rul_view(estimate), f"{_('PLANNING_RUL_ESTIMATED')}\n{_('PLANNING_RUL_ESTIMATED')}: 12.5 [8.0 - ...]")
check("another status is refused", (planning.parse_rul({"status": "doomed"}), planning.parse_rul([]), planning.rul_view(planning.parse_rul({"status": "not_rising"}))), (None, None, _("PLANNING_RUL_NOT_RISING")))

# -- a version train
PLAN = {
    "schema_version": "1.2", "train": "lote-1", "ok": False, "problems": ["blocked: x"],
    "items": [
        {"name": "HYDRA-UMC-SDK", "action": "update", "version": "0.4.5", "installed_version": "0.4.4", "reason": "older"},
        {"name": "HYDRA-UMC-DOCS", "action": "install", "version": "0.0.7", "installed_version": None},
    ],
}
train = planning.parse_train_plan(json.dumps(PLAN))
check("reads the items in order", [(i["name"], i["action"], i["installedVersion"]) for i in train["items"]], [("HYDRA-UMC-SDK", "update", "0.4.4"), ("HYDRA-UMC-DOCS", "install", None)])
tv = planning.train_view(train)
check("the view of a train with problems", (tv["name"], tv["okText"], tv["problems"], tv["rows"][1]),
      ("lote-1", "", [f"{_('PLANNING_TRAIN_PROBLEMS')}: blocked: x"], f"HYDRA-UMC-DOCS  {_('PLANNING_TRAIN_INSTALL')}  - -> 0.0.7"))
check("a train with no problems says so", planning.train_view(planning.parse_train_plan(json.dumps({**PLAN, "ok": True, "problems": []})))["okText"], _("PLANNING_TRAIN_OK"))
check("refuses what is not the stable output",
      [planning.parse_train_plan(x) for x in (json.dumps({**PLAN, "schema_version": "2.0"}), json.dumps({**PLAN, "schema_version": 1}), json.dumps({**PLAN, "items": None}),
                                              json.dumps({**PLAN, "items": [{"name": "x", "action": "format-disk", "version": "1"}]}), "plan: ok", "[]", "[" * 100000)],
      [None] * 7)

# -- the data lake
check("the switch of the window statistics from the status", [planning.switch_from_status(x) for x in (404, 400, 200, 503, None, 403)], ["off", "on", "on", "unknown", "unknown", "unknown"])
check("its sentence", planning.switch_text("off"), f"{_('PLANNING_DL_WINDOWS')}: {_('PLANNING_DL_OFF')}")

# -- the screen makes only the requests it is meant to make
try:
    from hydra_suite.net.client import HydraConnection  # noqa: F401  (needs httpx: the CI installs it)
    have_client = True
except ImportError:
    have_client = False
if have_client:
    from hydra_suite.net import client as client_module

    class Probe:
        calls = []

        async def _http(self, method, path, **kwargs):
            Probe.calls.append((method, path))
            raise client_module.httpx.ConnectError("down")

    probe = Probe()
    relay = client_module.HydraConnection.relay_request
    refused = []
    for combo in (("semantic-planner", "POST", "/release"), ("job-dispatcher", "POST", "/jobs/submit"), ("datalake", "POST", "/ingest"), ("datalake", "GET", "/rollups"), ("vla-engine", "POST", "/act")):
        try:
            asyncio.run(relay(probe, *combo))
            refused.append(False)
        except ValueError:
            refused.append(True)
    check("a request outside the few allowed ones is refused before it is sent", (refused, Probe.calls), ([True] * 5, []))
    check("an allowed request goes to the relay of the server and a connection failure is None",
          (asyncio.run(relay(probe, "semantic-planner", "POST", "/plan/simulate", {"steps": []})), Probe.calls), (None, [("POST", "/api/ai/semantic-planner/plan/simulate")]))
else:
    print("skip the client checks (httpx is not installed here)")
check("every sentence exists", all(_(k) != k for k in ("DOCK_ECOSYSTEM_PLANNING", "PLANNING_TITLE", "PLANNING_INTRO", "PLANNING_SIM_TITLE", "PLANNING_ETA_TITLE", "PLANNING_RUL_TITLE", "PLANNING_TRAIN_TITLE", "PLANNING_DL_TITLE", "PLANNING_DL_DOWNSAMPLING")), True)

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
