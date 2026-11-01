# =============================================================================
# HYDRA-UMC SUITE - panel_logic/planning.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Planning and operation screen without any window: how a plan is read, what the dry run answers, the estimates of the job
# dispatcher, the remaining useful life, a version train read from the output of `train plan --json` and the state of the window
# statistics of the data lake. Everything reaches the services through the relay of the server (/api/ai/<service>/...). The
# screen only reads or simulates: nothing here moves a robot, queues a job or installs a version, and an answer that claims to
# have executed something is refused instead of shown. STUDIO has the same screen (src/lib/planningApi.ts); the two read the same
# answers the same way.
# =============================================================================
from __future__ import annotations

import json
import math

from hydra_suite.i18n import _

#: The only requests the screen makes through the relay, as (service, method, path). Anything else is refused before it is sent.
ALLOWED_REQUESTS = frozenset(
    {
        ("semantic-planner", "POST", "/plan/simulate"),
        ("job-dispatcher", "GET", "/dispatch/eta"),
        ("anomaly-detector", "POST", "/rul"),
        ("datalake", "GET", "/windows"),
    }
)
MAX_PLAN_STEPS = 10000
MAX_RUL_POINTS = 1000
RUL_STATUSES = ("insufficient_data", "not_rising", "limit_reached", "estimated")
TRAIN_ACTIONS = ("install", "update", "downgrade", "keep", "blocked")
MAX_TRAIN_FILE_BYTES = 1_000_000


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def failure_text(status: int | None, body: object = None) -> str:
    """The sentence for an answer that is not a 200; "" for a 200. None means the server itself did not answer."""
    if status is None:
        return _("PLANNING_NETWORK")
    if status == 200:
        return ""
    if status == 404:
        return _("PLANNING_OFF")
    if status in (401, 403):
        return _("PLANNING_FORBIDDEN")
    if status == 503:
        return _("PLANNING_UNREACHABLE")
    if status in (400, 413):
        detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
        return _("PLANNING_INVALID") + detail if detail else _("PLANNING_HTTP")
    return _("PLANNING_HTTP")


def format_duration(ms: object) -> str:
    """"3 min 20 s" style text for a duration in milliseconds."""
    value = _number(ms)
    if value is None or value < 0:
        return "-"
    total = round(value / 1000)
    hours, minutes, seconds = total // 3600, total % 3600 // 60, total % 60
    if hours:
        return f"{hours} h {minutes} min"
    if minutes:
        return f"{minutes} min {seconds} s"
    return f"{seconds} s"


# -- the dry run of a plan ---------------------------------------------------------------------------------------------------------------

def parse_plan_request(text: str) -> dict | None:
    """A request for the dry run: a JSON object with a non-empty list of steps (at most MAX_PLAN_STEPS); None otherwise."""
    try:
        parsed = json.loads(text)
    except (ValueError, RecursionError):
        return None
    steps = parsed.get("steps") if isinstance(parsed, dict) else None
    if not isinstance(steps, list) or not 0 < len(steps) <= MAX_PLAN_STEPS:
        return None
    return parsed


def parse_simulation(raw: object) -> dict | None:
    """The answer of a dry run; None when it is not one (including an answer that claims to have executed, or to be executable)."""
    if not isinstance(raw, dict) or raw.get("executable") is not False or raw.get("executed") is not False:
        return None
    verdict = raw.get("verdict")
    if verdict not in ("accepted", "rejected"):
        return None
    violations = []
    for item in raw.get("violations") if isinstance(raw.get("violations"), list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("rule"), str):
            continue
        suggestion = item.get("suggestion")
        violations.append(
            {
                "rule": item["rule"],
                "stepId": _text(item.get("step_id")),
                "message": _text(item.get("message")) or "",
                "suggestion": None if suggestion is None else suggestion if isinstance(suggestion, str) else json.dumps(suggestion, separators=(",", ":")),
            }
        )
    if verdict == "accepted" and violations:
        return None  # an accepted plan that lists a violation is not an accepted plan
    timeline = []
    for item in raw.get("timeline") if isinstance(raw.get("timeline"), list) else []:
        if not isinstance(item, dict):
            continue
        start, end = _number(item.get("start_ms")), _number(item.get("end_ms"))
        if _text(item.get("step_id")) is None or start is None or end is None:
            continue
        timeline.append({"stepId": item["step_id"], "robot": _text(item.get("robot")) or "", "primitive": _text(item.get("primitive")) or "", "startMs": start, "endMs": end})
    return {"verdict": verdict, "violations": violations, "timeline": timeline, "makespanMs": _number(raw.get("makespan_ms"))}


def simulation_view(sim: dict) -> dict:
    """What the screen shows of a dry run, with the sentences in the language of the interface."""
    lines = []
    for violation in sim["violations"]:
        where = f" ({violation['stepId']})" if violation["stepId"] else ""
        extra = f" - {violation['suggestion']}" if violation["suggestion"] else ""
        lines.append(f"{violation['rule']}{where}: {violation['message']}{extra}")
    timeline = [
        f"{e['stepId']}  {e['robot']}  {e['primitive']}  {format_duration(e['startMs'])} - {format_duration(e['endMs'])}" for e in sim["timeline"]
    ]
    return {
        "accepted": sim["verdict"] == "accepted",
        "verdictText": _("PLANNING_SIM_ACCEPTED") if sim["verdict"] == "accepted" else _("PLANNING_SIM_REJECTED"),
        "notExecuted": _("PLANNING_SIM_NOT_EXECUTED"),
        "violations": lines,
        "timeline": timeline,
        "makespan": f"{_('PLANNING_SIM_MAKESPAN')}: {format_duration(sim['makespanMs'])}" if sim["makespanMs"] is not None else "",
    }


# -- the estimates of the dispatcher -----------------------------------------------------------------------------------------------------

def parse_eta(raw: object) -> dict | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("jobs"), list):
        return None
    generated = _number(raw.get("generatedAtMs"))
    if generated is None:
        return None
    jobs = []
    for item in raw["jobs"]:
        if not isinstance(item, dict) or not isinstance(item.get("jobId"), str) or not isinstance(item.get("status"), str):
            continue
        jobs.append(
            {
                "jobId": item["jobId"], "status": item["status"], "estimated": item.get("estimated") is True, "robotId": _text(item.get("robotId")),
                "endMs": _number(item.get("endMs")), "reason": _text(item.get("reason")),
                "lowMs": _number(item.get("endLowMs")), "highMs": _number(item.get("endHighMs")),
            }
        )
    return {"generatedAtMs": generated, "drainMs": _number(raw.get("drainMs")), "jobs": jobs}


def eta_view(eta: dict) -> dict:
    generated = eta["generatedAtMs"]
    rows = []
    for job in eta["jobs"]:
        if job["estimated"] and job["endMs"] is not None:
            when = format_duration(job["endMs"] - generated)
            if job["lowMs"] is not None and job["highMs"] is not None:
                when += f" [{format_duration(job['lowMs'] - generated)} - {format_duration(job['highMs'] - generated)}]"
        else:
            when = _("PLANNING_ETA_NO_ESTIMATE") + (f" ({job['reason']})" if job["reason"] else "")
        rows.append(f"{job['jobId']}  {job['status']}  {job['robotId'] or '-'}  {when}")
    drain = f"{_('PLANNING_ETA_DRAIN')} {format_duration(eta['drainMs'] - generated)}" if eta["drainMs"] is not None else ""
    return {"rows": rows, "drain": drain, "empty": _("PLANNING_ETA_EMPTY") if not rows else ""}


# -- the remaining useful life -----------------------------------------------------------------------------------------------------------

def parse_rul_points(text: str) -> list | None:
    """Points typed or pasted, one per line as `seconds, score`; None when a line is not that or there are too many or none."""
    points = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p for p in line.replace(",", " ").replace(";", " ").split() if p]
        if len(parts) != 2:
            return None
        try:
            t, score = float(parts[0]), float(parts[1])
        except ValueError:
            return None
        if not math.isfinite(t) or not math.isfinite(score):
            return None
        points.append({"t": t, "score": score})
        if len(points) > MAX_RUL_POINTS:
            return None
    return points or None


def parse_limit(text: str) -> float | None:
    cleaned = text.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_rul(raw: object) -> dict | None:
    if not isinstance(raw, dict) or raw.get("status") not in RUL_STATUSES:
        return None
    return {key: (raw["status"] if key == "status" else _number(raw.get(key))) for key in ("status", "points", "slopePerDay", "currentValue", "daysToLimit", "daysLow", "daysHigh")}


def rul_view(estimate: dict) -> str:
    text = _("PLANNING_RUL_" + estimate["status"].upper())
    if estimate["status"] == "estimated" and estimate["daysToLimit"] is not None:
        text += f"\n{_('PLANNING_RUL_ESTIMATED')}: {estimate['daysToLimit']:.1f}"
        if estimate["daysLow"] is not None:
            high = f"{estimate['daysHigh']:.1f}" if estimate["daysHigh"] is not None else "..."
            text += f" [{estimate['daysLow']:.1f} - {high}]"
    return text


# -- a version train as `train plan --json` wrote it -------------------------------------------------------------------------------------

def parse_train_plan(text: str) -> dict | None:
    """The output of `train plan --json` (schema 1.x); None when it is not that. A newer major version is refused instead of guessed at."""
    try:
        raw = json.loads(text)
    except (ValueError, RecursionError):
        return None
    if not isinstance(raw, dict):
        return None
    version = raw.get("schema_version")
    if not isinstance(version, str) or not version.startswith("1.") or not version[2:].isdigit():
        return None
    if not isinstance(raw.get("train"), str) or not isinstance(raw.get("ok"), bool) or not isinstance(raw.get("items"), list):
        return None
    items = []
    for item in raw["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or item.get("action") not in TRAIN_ACTIONS:
            return None
        items.append(
            {"name": item["name"], "action": item["action"], "version": _text(item.get("version")) or "", "installedVersion": _text(item.get("installed_version")), "reason": _text(item.get("reason"))}
        )
    problems = [p for p in raw["problems"] if isinstance(p, str)] if isinstance(raw.get("problems"), list) else []
    return {"train": raw["train"], "ok": raw["ok"], "problems": problems, "items": items}


def train_view(train: dict) -> dict:
    rows = [
        f"{item['name']}  {_('PLANNING_TRAIN_' + item['action'].upper())}  {item['installedVersion'] or '-'} -> {item['version']}"
        + (f"  {item['reason']}" if item["reason"] else "")
        for item in train["items"]
    ]
    return {
        "name": train["train"],
        "okText": _("PLANNING_TRAIN_OK") if train["ok"] else "",
        "problems": [] if train["ok"] else [f"{_('PLANNING_TRAIN_PROBLEMS')}: {p}" for p in train["problems"]],
        "rows": rows,
    }


# -- the window statistics of the data lake ----------------------------------------------------------------------------------------------

def switch_from_status(status: int | None) -> str:
    """"on", "off" or "unknown" from the answer to a read of /windows without parameters: 404 means the switch is off, 400 (or 200) that it is on."""
    if status == 404:
        return "off"
    if status in (200, 400):
        return "on"
    return "unknown"


def switch_text(state: str) -> str:
    return f"{_('PLANNING_DL_WINDOWS')}: {_('PLANNING_DL_' + state.upper())}"
