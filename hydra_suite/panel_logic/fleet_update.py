# =============================================================================
# HYDRA-UMC SUITE - hydra_suite/panel_logic/fleet_update.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Every program installed on the device against its newest release, without any window toolkit (GET /api/admin/fleet-update of the server).

The device does the work (a copy of each program with its unit files, the installer of the program, the checks, the way back, one program at a time and
stopping at the first failure); this module reads the progress file the server forwards defensively (a state, an action or a step it does not know is shown as
not known, never as done or as up to date), decides what may be started, follows the run until it ends and builds what the screen shows. The server restarts at
the end of its own update, so the answers fail for a while: a refused connection or a 502 is a reason to wait, never a failure, and the follower gives up with a
message only after a limit of silence.

A device with the root helper (signed packages) also asks, at the second step, for the identifier of the look the person saw (`planId`) and, while it says so, a
one-time code of six digits; it can go back to the version kept of a program. Applying is off by default behind the same switch as the update of the three main programs (kept in the configuration file of the program); even with it on,
every update and every taking up asks first, naming the programs and their versions. The same rules as the panel of STUDIO."""
from __future__ import annotations

import asyncio
import re
import time
from typing import Awaitable, Callable

from hydra_suite.i18n import _
from hydra_suite.panel_logic.self_update import apply_from_config, config_update_apply  # noqa: F401  (the switch is the one of the main programs)

RUN_STATES = ("planned", "running", "done", "failed", "blocked", "interrupted")
ROW_STATES = ("waiting", "running", "done", "failed", "rolled_back", "interrupted", "skipped", "blocked")
ROW_ACTIONS = ("update", "current", "skip", "review")
#: The steps of one program, in the order the device goes through them.
STEPS = ("disk", "fetching", "backup", "building", "installing", "verifying", "done")
ERRORS = (
    "low_disk", "fetch_failed", "tag_mismatch", "tag_unsigned", "checkout_failed", "backup_failed", "build_failed", "installer_failed", "version_mismatch",
    "not_healthy", "journal_errors", "sdk_not_importable", "interrupted", "unexpected",
    # the root helper of the device (signed packages)
    "account_failed", "bad_package", "deploy_failed", "download_failed", "first_install_off", "layout_unknown", "migration_failed", "missing_system_package",
    "needs_first_setup", "no_earlier_release", "not_installed", "not_newer", "restart_failed", "rollback_failed", "signature_invalid", "units_failed",
    "write_failed", "wrong_python",
)
REASONS = (
    "special_stack", "no_release", "version_unreadable", "installed_newer", "unit_inactive", "repo_dirty", "goes_with_server", "not_asked", "no_checkout",
    "migrated_needs_packages", "migrated_no_package", "own_package", "first_install", "needs_newer_rustc", "no_signed_package",
)
#: What the root helper accepts: the one-time code and the identifier of a look.
ONE_TIME_CODE = re.compile(r"^[0-9]{6}$")
PLAN_ID = re.compile(r"^[0-9a-f]{32}$")
START_FAILURES = ("disabled", "forbidden", "busy", "refused", "network")
#: What the server needs free to build and install, in MB (the device checks the same numbers).
SERVER_NEEDS_MB = 2500
INTERVAL_S = 2.0
SILENCE_LIMIT_S = 300.0
#: The name of a program as the server accepts it: nothing else is ever sent.
NAME = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
#: Rows in the state where a program can be taken up again by itself.
RESUMABLE = ("interrupted", "failed", "rolled_back", "blocked")


def _text(value: object, limit: int = 120) -> str | None:
    return value[:limit] if isinstance(value, str) and value.strip() else None


def _whole(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and 0 <= value < 1e12 else None


def _pick(value: object, known: tuple[str, ...]) -> str:
    """The value when this program knows it, "unknown" otherwise: a state that is not known is never taken for another one."""
    return value if isinstance(value, str) and value in known else "unknown"


# -- reading the answers ---------------------------------------------------------------------------------------------------------------------------


def parse_row(data: object) -> dict | None:
    """One program of the progress file, or None when it has no valid name."""
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not NAME.match(data["name"]):
        return None
    raw_log = data.get("log")
    log = []
    if isinstance(raw_log, list):
        for line in raw_log:
            if isinstance(line, dict) and isinstance(line.get("text"), str):
                log.append({"at": str(line.get("at") or "")[:30], "text": line["text"][:300]})
    return {
        "name": data["name"],
        "kind": data["kind"] if data.get("kind") in ("repo", "svc", "frontend") else "svc",
        "repo": str(data.get("repo") or "")[:80],
        "installed": _text(data.get("installed"), 40),
        "latest": _text(data.get("latest"), 40),
        "action": _pick(data.get("action"), ROW_ACTIONS),
        "reason": str(data.get("reason") or "")[:60],
        "state": _pick(data.get("state"), ROW_STATES),
        "step": str(data.get("step") or "")[:30],
        "substep": str(data.get("substep") or "")[:40],
        "substeps": _whole(data.get("substeps")) or 0,
        "detail": str(data.get("detail") or "")[:200],
        "error": str(data.get("error") or "")[:40],
        "elapsedS": _whole(data.get("elapsedS")) or 0,
        "freeMb": _whole(data.get("freeMb")),
        "needMb": _whole(data.get("needMb")),
        "unitRestored": data["unitRestored"] if isinstance(data.get("unitRestored"), bool) else None,
        "log": log[-30:],
        "previous": _text(data.get("previous"), 40),
    }


def parse_report(data: object) -> dict | None:
    """The progress file as the screen uses it, or None when there is none (no look yet) or it is not that file. A state of the run that is not known is "unknown"."""
    if not isinstance(data, dict) or not isinstance(data.get("services"), list):
        return None
    disk = data.get("disk") if isinstance(data.get("disk"), dict) else {}
    return {
        "id": str(data.get("id") or "")[:40],
        "mode": "run" if data.get("mode") == "run" else "plan",
        "state": _pick(data.get("state"), RUN_STATES),
        "updatedAt": str(data.get("updatedAt") or "")[:30],
        "error": str(data.get("error") or "")[:60],
        "stoppedAt": str(data.get("stoppedAt") or "")[:60],
        "requireSignedTags": data.get("requireSignedTags") is True,
        "rootFreeMb": _whole(disk.get("rootFreeMb")),
        "workspaceFreeMb": _whole(disk.get("workspaceFreeMb")),
        "services": [row for row in (parse_row(entry) for entry in data["services"]) if row is not None],
        # root helper only: a missing totpRequired means a code is asked (the server decides the same way)
        "helper": "root" if data.get("helper") == "root" else "",
        "planId": data["planId"] if data.get("helper") == "root" and isinstance(data.get("planId"), str) and PLAN_ID.match(data["planId"]) else "",
        "totpRequired": data.get("helper") == "root" and data.get("totpRequired") is not False,
    }


def parse_status(data: object) -> dict | None:
    """The answer of the routes of the update of everything installed ({applyEnabled, busy, report}), or None when it is not that answer. `report` may be null
    (nothing looked at yet)."""
    if not isinstance(data, dict) or "report" not in data or not (data["report"] is None or isinstance(data["report"], dict)):
        return None
    report = parse_report(data["report"])
    if data["report"] is not None and report is None:
        return None  # a report that is not the file is not a report
    return {"applyEnabled": data.get("applyEnabled") is True, "busy": data.get("busy") is True, "report": report}


def classify_read(result: tuple[int, object] | None) -> tuple[str, dict | None]:
    """("ok", status) for a good answer; otherwise why not: "unsupported", "forbidden", "http", "malformed" or "network"."""
    if result is None:
        return "network", None
    status, body = result
    if status == 404:
        return "unsupported", None
    if status in (401, 403):
        return "forbidden", None
    if status != 200:
        return "http", None
    parsed = parse_status(body)
    return ("ok", parsed) if parsed is not None else ("malformed", None)


def classify_start(result: tuple[int, object] | None) -> tuple[str, dict | None]:
    """("ok", status) when the server did what was asked (a look, the start of a run, the taking up of a program); otherwise one of START_FAILURES. A 404 is the
    server with the look or applying switched off; a 423 is listen-only mode, which refuses before the request leaves the program."""
    if result is None:
        return "network", None
    status, body = result
    if status == 404:
        return "disabled", None
    if status in (401, 403, 423):
        return "forbidden", None
    if status == 409:
        return "busy", None
    if not 200 <= status < 300:
        return "refused", None
    parsed = parse_status(body)
    return ("ok", parsed) if parsed is not None else ("refused", None)


def classify_run_read(result: tuple[int, object] | None) -> tuple[str, dict | None]:
    """One look at the progress during a run. A refused connection, a proxy that answers 502 to 504 while the server restarts and a body that is not the file all
    mean "wait": none of them says the run failed. Only a refused session stops the follower."""
    if result is None:
        return "wait", None
    status, body = result
    if status in (401, 403):
        return "stop", None
    if status != 200:
        return "wait", None
    parsed = parse_status(body)
    return ("status", parsed) if parsed is not None else ("wait", None)


# -- the run ---------------------------------------------------------------------------------------------------------------------------------------


def running(status: dict | None) -> bool:
    """Whether a run is going on. A run that stopped writing is told as interrupted by the server, and so it is not "running" here."""
    report = status["report"] if status else None
    return report is not None and report["state"] == "running"


def updatable(report: dict | None) -> list[dict]:
    """The programs the plan marks to update, in order. The frontend goes with the server. One that is done, or whose action or state this program does not
    know, is not offered."""
    if report is None or report["state"] in ("running", "unknown"):
        return []
    return [row for row in report["services"] if row["action"] == "update" and row["kind"] != "frontend" and row["state"] not in ("done", "running", "unknown")]


def resumable(row: dict) -> bool:
    """A program that can be taken up again by itself."""
    return row["state"] in RESUMABLE


def step_progress(row: dict) -> float:
    """How far a program is through its steps, 0 to 1 (0 when the step is not known: nothing is claimed)."""
    if row["state"] == "done":
        return 1.0
    if row["step"] not in STEPS:
        return 0.0
    return min(0.95, STEPS.index(row["step"]) / (len(STEPS) - 1))


def disk_low_for_server(report: dict | None) -> bool:
    """Whether there is too little disk for the server to be built, given what the last look found. A reading that is not known says nothing."""
    if report is None:
        return False
    server = next((row for row in report["services"] if row["name"] == "server"), None)
    if server is None or server["action"] != "update":
        return False
    readings = [value for value in (report["rootFreeMb"], report["workspaceFreeMb"]) if value is not None]
    return bool(readings) and min(readings) < SERVER_NEEDS_MB


def can_apply(apply_on: bool, status: dict | None, busy: bool) -> bool:
    """Whether the buttons may be on at all: the switch of this program, the switch of the server and no look or run going on. Both switches must say yes."""
    return bool(apply_on and status is not None and status["applyEnabled"] and not status["busy"] and not running(status) and not busy)


def needs_code(status: dict | None) -> bool:
    """Whether the second step must bring a one-time code."""
    report = status["report"] if status else None
    return bool(report and report["totpRequired"])


def confirmation(status: dict | None, code: str) -> dict[str, str] | None:
    """What the second step brings to the root helper ({} for any other device): the identifier of the look and the code. None when a code is needed and what was
    typed is not six digits, or a code that is not six digits was typed at all."""
    report = status["report"] if status else None
    if report is None or report["helper"] != "root":
        return {}
    code = code.strip()
    if (code and not ONE_TIME_CODE.match(code)) or (report["totpRequired"] and not code):
        return None
    return {**({"planId": report["planId"]} if report["planId"] else {}), **({"code": code} if code else {})}


def can_go_back(report: dict | None, row: dict) -> bool:
    """A program the root helper keeps an earlier version of."""
    return bool(report and report["helper"] == "root" and row["previous"] and row["state"] != "running")


def may_start(action: str, names: list[str], apply_on: bool, status: dict | None, busy: bool = False) -> list[dict] | None:
    """The programs `action` ("apply" or "resume") may start on, or None. An update needs programs the plan marks to update; taking up needs exactly one program
    in a state where it can be taken up. The screen only offers what this allows, and it is asked again at the confirmation."""
    if action not in ("apply", "resume", "rollback") or not can_apply(apply_on, status, busy) or not names or len(set(names)) != len(names):
        return None
    if not all(isinstance(name, str) and NAME.match(name) for name in names):
        return None
    report = status["report"] if status is not None else None
    if report is None:
        return None
    if action == "apply":
        fits = {row["name"]: row for row in updatable(report)}
        return [fits[name] for name in names] if all(name in fits for name in names) else None
    row = next((entry for entry in report["services"] if entry["name"] == names[0]), None)
    if len(names) != 1 or row is None:
        return None
    fits = can_go_back(report, row) if action == "rollback" else resumable(row)
    return [row] if fits else None


async def follow_run(
    read: Callable[[], Awaitable[tuple[str, dict | None]]],
    on_status: Callable[[dict], None],
    on_waiting: Callable[[int], None],
    *,
    interval: float | None = None,
    silence_limit: float | None = None,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    cancelled: Callable[[], bool] = lambda: False,
) -> tuple[str, object]:
    """Follows the run until the file stops saying it is running, asking again and again while the server is away; gives up only after `silence_limit` seconds
    without a single answer. Returns ("ended", status), ("silent", seconds) or ("stopped", "forbidden" | "cancelled")."""
    interval = INTERVAL_S if interval is None else interval
    silence_limit = SILENCE_LIMIT_S if silence_limit is None else silence_limit
    last_answer = now()
    while True:
        if cancelled():
            return "stopped", "cancelled"
        kind, status = await read()
        if cancelled():
            return "stopped", "cancelled"
        if kind == "stop":
            return "stopped", "forbidden"
        if kind == "status" and status is not None:
            last_answer = now()
            on_status(status)
            if not running(status):
                return "ended", status
        else:
            silent = now() - last_answer
            on_waiting(int(silent))
            if silent >= silence_limit:
                return "silent", int(silent)
        await sleep(interval)


# -- what the screen shows -------------------------------------------------------------------------------------------------------------------------


def error_text(row: dict) -> str:
    """The sentence of the reason a program failed; a code this program does not know has the general sentence."""
    code = row["error"] if row["error"] in ERRORS else "unexpected"
    return _("FLEETUPD_ERR_" + code.upper(), free=row["freeMb"] if row["freeMb"] is not None else "?", need=row["needMb"] if row["needMb"] is not None else "?")


def reason_text(code: str) -> str:
    return _("FLEETUPD_REASON_" + code.upper()) if code in REASONS else ""


def state_label(state: str) -> str:
    return _("COMMON_DONE") if state == "done" else _("FLEETUPD_STATE_" + state.upper()) if state in ROW_STATES else _("SELFUPD_STATE_UNKNOWN")


def action_label(action: str) -> str:
    return _("FLEETUPD_ACTION_" + action.upper()) if action in ROW_ACTIONS else _("SELFUPD_STATE_UNKNOWN")


def step_label(step: str) -> str:
    return _("COMMON_DONE") if step == "done" else _("FLEETUPD_STEP_" + step.upper()) if step in STEPS else _("SELFUPD_STATE_UNKNOWN")


def versions_line(row: dict) -> str:
    return f"{row['installed'] or '?'} -> {row['latest'] or '?'}"


def program_line(row: dict) -> str:
    return f"{row['name']} ({versions_line(row)})"


def progress_text(row: dict) -> str:
    if row["state"] == "running":
        sub = f" ({row['substep']})" if row["substeps"] > 0 and row["substep"] else ""
        return step_label(row["step"] or "disk") + sub + (f" - {row['elapsedS']} s" if row["elapsedS"] > 0 else "")
    if row["error"]:
        return error_text(row)
    return state_label(row["state"])


def tone(row: dict) -> str:
    if row["state"] in ("failed", "rolled_back", "blocked"):
        return "bad"
    if row["state"] == "done":
        return "good"
    return "unknown" if row["state"] == "unknown" else "normal"


def row_view(row: dict, allowed: bool, report: dict | None = None) -> dict:
    """One program of the table. The progress is shown for a program that will be updated or has left its first state; a button to take it up again only when
    both switches allow it."""
    shows_progress = row["action"] == "update" or row["state"] not in ("waiting",)
    return {
        "name": row["name"],
        "installed": row["installed"] or "-",
        "latest": row["latest"] or "-",
        "action": row["action"],
        "actionLabel": action_label(row["action"]),
        "reason": reason_text(row["reason"]),
        "state": row["state"],
        "tone": tone(row),
        "showsProgress": shows_progress,
        "progressText": progress_text(row) if shows_progress else "",
        "progress": step_progress(row),
        "running": row["state"] == "running",
        "detail": row["detail"] if shows_progress and (row["state"] == "running" or row["error"]) else "",
        "unitWarning": _("FLEETUPD_UNIT_NOT_RESTORED") if row["unitRestored"] is False else "",
        "canTakeUp": allowed and resumable(row),
        "canGoBack": allowed and can_go_back(report, row),
    }


def run_text(report: dict | None) -> str:
    if report is None:
        return _("FLEETUPD_NO_PLAN")
    name = report["stoppedAt"] or report["error"]
    if report["state"] == "failed":
        return _("FLEETUPD_RUN_FAILED", name=name)
    if report["state"] == "blocked":
        return _("FLEETUPD_RUN_BLOCKED", name=name)
    return _("FLEETUPD_RUN_" + report["state"].upper()) if report["state"] in RUN_STATES else _("SELFUPD_STATE_UNKNOWN")


def mode_text(apply_on: bool, status: dict) -> str:
    if not apply_on:
        return _("SELFUPD_MODE_CHECK_ONLY")
    return _("FLEETUPD_MODE_APPLY") if status["applyEnabled"] else _("SELFUPD_MODE_SERVER_OFF")


def confirm_text(pending: dict | None, status: dict | None) -> str:
    """The question of the confirmation: the programs and their versions, and that the server restarts at the end when it is one of them. An empty text when the
    request no longer fits what is on screen."""
    if pending is None or status is None:
        return ""
    chosen = may_start(pending["action"], pending["names"], True, {**status, "applyEnabled": True, "busy": False}, False)
    if chosen is None:
        return ""
    if pending["action"] == "rollback":
        return _("FLEETUPD_CONFIRM_BACK", names=program_line(chosen[0]))
    if pending["action"] == "resume":
        return _("FLEETUPD_CONFIRM_RESUME", program=chosen[0]["name"], versions=versions_line(chosen[0]))
    text = _("FLEETUPD_CONFIRM_BODY", count=len(chosen), programs=", ".join(program_line(row) for row in chosen))
    return text + (" " + _("FLEETUPD_CONFIRM_SERVER") if any(row["name"] == "server" for row in chosen) else "")


def start_failure_text(reason: str) -> str:
    if reason == "busy":
        return _("FLEETUPD_START_BUSY")
    return _("SELFUPD_START_" + reason.upper()) if reason in START_FAILURES else _("SELFUPD_START_REFUSED")


def read_failure_text(kind: str) -> str:
    return {
        "unsupported": _("FLEETUPD_UNSUPPORTED"),
        "forbidden": _("SELFUPD_FORBIDDEN"),
        "no_server": _("LBL_ES_NO_ACTIVE_SERVER"),
    }.get(kind, _("SELFUPD_LOAD_ERROR"))


def view(
    status: dict | None, failure: str, apply_on: bool, silent: int | None, gave_up: bool, pending: dict | None, message: str, looking: bool,
) -> dict:
    """Everything the screen shows. `pending` is the update or taking up that waits for the confirmation ({"action", "names"}), `failure` the kind of the last
    failed read ("" : none)."""
    report = status["report"] if status is not None else None
    is_running = running(status)
    allowed = can_apply(apply_on, status, looking)
    rows = [row_view(row, allowed, report) for row in report["services"]] if report is not None else []
    todo = [row["name"] for row in updatable(report)]
    return {
        "title": _("FLEETUPD_TITLE"),
        "intro": _("FLEETUPD_INTRO"),
        "failure": read_failure_text(failure) if failure else "",
        "loaded": status is not None,
        "runText": run_text(report) if status is not None else "",
        "rows": rows,
        "columns": [_("SELFUPD_COL_PROGRAM"), _("SELFUPD_COL_INSTALLED"), _("FLEETUPD_COL_LATEST"), _("FLEETUPD_COL_ACTION"), _("FLEETUPD_COL_PROGRESS")],
        "lookLabel": _("FLEETUPD_LOOKING") if looking else _("FLEETUPD_LOOK"),
        "canLook": status is not None and not looking and not is_running,
        "updateAllLabel": _("FLEETUPD_UPDATE_ALL"),
        "canUpdateAll": allowed and bool(todo),
        "takeUpLabel": _("FLEETUPD_RESUME"),
        "goBackLabel": _("FLEETUPD_GO_BACK"),
        "needsCode": needs_code(status),
        "codeLabel": _("FLEETUPD_CODE_LABEL"),
        "mode": mode_text(apply_on, status) if status is not None else "",
        "disk": _("FLEETUPD_DISK_LINE", root=report["rootFreeMb"], workspace=report["workspaceFreeMb"] if report["workspaceFreeMb"] is not None else "?")
        if report is not None and report["rootFreeMb"] is not None else "",
        "diskLow": _("FLEETUPD_DISK_LOW", need=SERVER_NEEDS_MB) if disk_low_for_server(report) else "",
        "confirm": confirm_text(pending, status),
        "confirmTitle": _("FLEETUPD_CONFIRM_TITLE"),
        "confirmYes": _("COMMON_CONFIRM"),
        "confirmNo": _("COMMON_CANCEL"),
        "message": message,
        "interrupted": _("FLEETUPD_RUN_INTERRUPTED") if report is not None and report["state"] == "interrupted" else "",
        "waiting": _("FLEETUPD_WAITING", seconds=silent) if silent is not None and is_running and not gave_up else "",
        "gaveUp": _("FLEETUPD_GAVE_UP") if gave_up else "",
        "lookAgain": _("SELFUPD_LOOK_AGAIN"),
        "running": is_running,
        "todo": todo,
    }


EMPTY_VIEW: dict = {"title": "", "intro": "", "failure": "", "loaded": False, "runText": "", "rows": [], "columns": [], "lookLabel": "", "canLook": False, "updateAllLabel": "",
                    "canUpdateAll": False, "takeUpLabel": "", "goBackLabel": "", "needsCode": False, "codeLabel": "", "mode": "", "disk": "", "diskLow": "", "confirm": "", "confirmTitle": "", "confirmYes": "", "confirmNo": "",
                    "message": "", "interrupted": "", "waiting": "", "gaveUp": "", "lookAgain": "", "running": False, "todo": []}
