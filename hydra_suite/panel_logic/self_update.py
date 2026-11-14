# =============================================================================
# HYDRA-UMC SUITE - hydra_suite/panel_logic/self_update.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The programs of the machine against their newest signed release, without any window toolkit (GET /api/admin/self-update of the server).

The server looks up the newest signed release of the server, of Studio and of the agent of the operating system. This module reads what it reports defensively
(a state it does not know is shown as not known, never as up to date), reads the job that an update or a way back starts, follows that job until it ends and
builds what the screen shows. The server restarts in the middle of its own update, so the answers fail for a while: the follower keeps asking (a short interval,
a limit of silence with a message, never a screen that waits for ever) and ends when the job ends, whatever it says.

Applying is off by default behind a switch kept in the configuration file of the program; even with it on, every update and every way back asks first, naming
the program and the two versions. The same rules as the section of STUDIO."""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

from hydra_suite.i18n import _

CONFIG_KEY = "self_update_apply"
COMPONENTS = ("server", "studio", "os-agent")
STEPS = ("checking", "downloading", "verifying", "applying", "restarting", "done", "failed")
#: The steps shown as a line of progress (failed is not a step but the end of one).
PROGRESS_STEPS = ("checking", "downloading", "verifying", "applying", "restarting", "done")
FAILURES = (
    "no_release", "already_current", "no_signed_package", "download_failed", "package_too_large", "signature_invalid",
    "no_earlier_release", "start_failed", "rolled_back", "deploy_failed", "timeout", "interrupted",
)
ITEM_STATES = ("current", "behind", "ahead", "unknown")
START_FAILURES = ("disabled", "forbidden", "busy", "refused", "network")
INTERVAL_S = 1.5
SILENCE_LIMIT_S = 240.0
ACTIONS = ("apply", "rollback")


def apply_from_config(config: object) -> bool:
    """Whether applying updates from this program is allowed: off unless the configuration says exactly true."""
    return isinstance(config, dict) and config.get(CONFIG_KEY) is True


def config_update_apply(on: bool) -> dict:
    return {CONFIG_KEY: bool(on)}


def _text(value: object, limit: int = 120) -> str | None:
    return value[:limit] if isinstance(value, str) and value.strip() else None


# -- reading the answers ---------------------------------------------------------------------------------------------------------------------------


def parse_job(data: object) -> dict | None:
    """A job as the screen uses it, or None when the answer is not a job (no id, a program of the three or a step this program knows)."""
    if not isinstance(data, dict):
        return None
    job_id, component, state = _text(data.get("id")), data.get("component"), data.get("state")
    if job_id is None or component not in COMPONENTS or state not in STEPS:
        return None
    raw_log = data.get("log")
    log = []
    if isinstance(raw_log, list):
        for line in raw_log:
            if isinstance(line, dict) and line.get("step") in STEPS and isinstance(line.get("text"), str):
                log.append({"at": str(line.get("at") or ""), "step": line["step"], "text": line["text"][:300]})
    return {
        "id": job_id,
        "action": "rollback" if data.get("action") == "rollback" else "apply",
        "component": component,
        "state": state,
        "fromVersion": _text(data.get("fromVersion")),
        "targetVersion": _text(data.get("targetVersion")),
        "error": _text(data.get("error")),
        "detail": str(data.get("detail") or "")[:300],
        "log": log[-60:],
    }


def parse_status(data: object) -> dict | None:
    """The answer of GET /api/admin/self-update, or None when it is not that answer. An item with a program this program does not know is dropped; a state it
    does not know is "unknown"."""
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return None
    items = []
    for entry in data["items"]:
        if not isinstance(entry, dict) or entry.get("id") not in COMPONENTS:
            continue
        items.append({
            "id": entry["id"],
            "repo": str(entry.get("repo") or "")[:120],
            "installed": _text(entry.get("installed")),
            "previous": _text(entry.get("previous")),
            "latest": _text(entry.get("latest")),
            "state": entry.get("state") if entry.get("state") in ITEM_STATES else "unknown",
            "signedPackage": entry.get("signedPackage") is True,
        })
    return {
        "items": items,
        "applyEnabled": data.get("applyEnabled") is True,
        "rateLimited": data.get("rateLimited") is True,
        "job": parse_job(data.get("job")),
    }


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
    """("ok", job) when the server started the job; otherwise one of START_FAILURES. A 404 is the server with applying switched off."""
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
    job = parse_job(body)
    return ("ok", job) if job is not None else ("refused", None)


def classify_job_read(result: tuple[int, object] | None, job_id: str) -> tuple[str, dict | None]:
    """One look at the job. A refused connection, a proxy that answers 502 to 504 while the server restarts and a body that is not that job all mean "wait":
    none of them says the update failed. Only a refused session stops the follower."""
    if result is None:
        return "wait", None
    status, body = result
    if status in (401, 403):
        return "stop", None
    if status != 200:
        return "wait", None
    job = parse_job(body)
    return ("job", job) if job is not None and job["id"] == job_id else ("wait", None)


# -- the job ---------------------------------------------------------------------------------------------------------------------------------------


def running(job: dict | None) -> bool:
    """Whether a job is still going on (the server may be restarting; it has not said it ended)."""
    return job is not None and job["state"] not in ("done", "failed")


def progress_index(job: dict) -> int:
    """The index of the step of the line of progress a job is at (-1 when it failed before the first one)."""
    if job["state"] == "failed":
        seen = [PROGRESS_STEPS.index(line["step"]) for line in job["log"] if line["step"] in PROGRESS_STEPS]
        return max([-1, *seen])
    return PROGRESS_STEPS.index(job["state"])


def step_marks(job: dict) -> list[dict]:
    """The line of progress: every step with its mark ("done", "now", "next" or "failed")."""
    at = progress_index(job)
    marks = []
    for index, step in enumerate(PROGRESS_STEPS):
        if job["state"] == "failed" and index == at + 1:
            mark = "failed"
        elif index < at or (index == at and job["state"] in ("done", "failed")):
            mark = "done"
        elif index == at:
            mark = "now"
        else:
            mark = "next"
        marks.append({"step": step, "label": _("SELFUPD_STEP_" + step.upper()), "mark": mark})
    return marks


def failure_text(code: str | None) -> str:
    """The sentence that says why a job failed; a reason this program does not know has the general sentence."""
    return _("SELFUPD_ERR_" + code.upper()) if code in FAILURES else _("SELFUPD_ERR_GENERIC")


def start_failure_text(reason: str) -> str:
    return _("SELFUPD_START_" + reason.upper()) if reason in START_FAILURES else _("SELFUPD_START_REFUSED")


async def follow_job(
    job_id: str,
    read: Callable[[str], Awaitable[tuple[str, dict | None]]],
    on_job: Callable[[dict], None],
    on_waiting: Callable[[int], None],
    *,
    interval: float | None = None,
    silence_limit: float | None = None,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    cancelled: Callable[[], bool] = lambda: False,
) -> tuple[str, object]:
    """Follows a job until it ends (done or failed), asking again and again while the server is away; gives up only after `silence_limit` seconds without a
    single answer. Returns ("ended", job), ("silent", seconds) or ("stopped", "forbidden" | "cancelled")."""
    interval = INTERVAL_S if interval is None else interval
    silence_limit = SILENCE_LIMIT_S if silence_limit is None else silence_limit
    last_answer = now()
    while True:
        if cancelled():
            return "stopped", "cancelled"
        kind, job = await read(job_id)
        if cancelled():
            return "stopped", "cancelled"
        if kind == "stop":
            return "stopped", "forbidden"
        if kind == "job" and job is not None:
            last_answer = now()
            on_job(job)
            if not running(job):
                return "ended", job
        else:
            silent = now() - last_answer
            on_waiting(int(silent))
            if silent >= silence_limit:
                return "silent", int(silent)
        await sleep(interval)


# -- what the screen shows -------------------------------------------------------------------------------------------------------------------------


def component_label(component: str) -> str:
    return _("SELFUPD_COMPONENT_" + component.replace("-", "_").upper())


def versions_line(item: dict, action: str) -> str:
    target = item["previous"] if action == "rollback" else item["latest"]
    return f"{item['installed'] or '?'} -> {target or '?'}"


def can_apply(apply_on: bool, status: dict | None, busy_job: bool) -> bool:
    """Whether the buttons may be on at all: the switch of this program, the switch of the server and no job going on. Both switches must say yes."""
    return bool(apply_on and status is not None and status["applyEnabled"] and not busy_job)


def item_row(item: dict, allowed: bool) -> dict:
    """One program of the table, with whether each button is on. Update needs a program that is behind and a signed package; going back needs an earlier release."""
    behind = item["state"] == "behind"
    return {
        "id": item["id"],
        "title": component_label(item["id"]),
        "repo": item["repo"],
        "installed": item["installed"] or "-",
        "previous": item["previous"] or "-",
        "latest": item["latest"] or "-",
        "state": item["state"],
        "stateLabel": _("SELFUPD_STATE_" + item["state"].upper()),
        "note": _("SELFUPD_NO_PACKAGE") if behind and not item["signedPackage"] else "",
        "canUpdate": allowed and behind and item["signedPackage"],
        "canGoBack": allowed and item["previous"] is not None,
    }


def mode_text(apply_on: bool, status: dict) -> str:
    text = _("SELFUPD_MODE_CHECK_ONLY") if not apply_on else _("SELFUPD_MODE_APPLY") if status["applyEnabled"] else _("SELFUPD_MODE_SERVER_OFF")
    return text + (" " + _("SELFUPD_RATE_LIMITED") if status["rateLimited"] else "")


def confirm_text(action: str, item: dict) -> str:
    key = "SELFUPD_CONFIRM_APPLY" if action == "apply" else "SELFUPD_CONFIRM_ROLLBACK"
    return _(key, program=component_label(item["id"]), versions=versions_line(item, action))


def job_view(job: dict | None, silent: int | None, gave_up: bool) -> dict:
    """The job card; an empty dict when there is no job to show."""
    if job is None:
        return {}
    title = _("SELFUPD_JOB_APPLY" if job["action"] == "apply" else "SELFUPD_JOB_ROLLBACK", program=component_label(job["component"]))
    done = _("SELFUPD_DONE_APPLY" if job["action"] == "apply" else "SELFUPD_DONE_ROLLBACK", version=job["targetVersion"] or "?") if job["state"] == "done" else ""
    failed = failure_text(job["error"]) if job["state"] == "failed" else ""
    waiting = _("SELFUPD_WAITING", seconds=silent) if silent is not None and running(job) and not gave_up else ""
    return {
        "title": title,
        "versions": f"{job['fromVersion'] or '?'} -> {job['targetVersion'] or '?'}",
        "steps": step_marks(job),
        "done": done,
        "failed": failed,
        "detail": job["detail"] if job["state"] == "failed" else "",
        "waiting": waiting,
        "gaveUp": _("SELFUPD_GAVE_UP") if gave_up else "",
        "lookAgain": _("SELFUPD_LOOK_AGAIN"),
        "running": running(job),
        "log": "\n".join(f"{line['at'][11:19]} {line['step']}: {line['text']}" for line in job["log"]),
    }


def read_failure_text(kind: str) -> str:
    return {
        "unsupported": _("SELFUPD_UNSUPPORTED"),
        "forbidden": _("SELFUPD_FORBIDDEN"),
        "no_server": _("LBL_ES_NO_ACTIVE_SERVER"),
    }.get(kind, _("SELFUPD_LOAD_ERROR"))


def may_start(action: str, component: str, apply_on: bool, status: dict | None, job: dict | None) -> dict | None:
    """The program of the table that `action` may start on, or None. Both switches must say yes, no job may be going on, an update needs a program that is
    behind with a signed package and going back needs an earlier release. The screen only offers what this allows, and it is asked again at the confirmation."""
    if action not in ACTIONS or not can_apply(apply_on, status, running(job)):
        return None
    item = next((entry for entry in status["items"] if entry["id"] == component), None) if status is not None else None
    if item is None:
        return None
    if action == "apply":
        return item if item["state"] == "behind" and item["signedPackage"] else None
    return item if item["previous"] is not None else None


def view(
    status: dict | None, failure: str, apply_on: bool, job: dict | None, silent: int | None, gave_up: bool, pending: dict | None, message: str, busy: bool,
) -> dict:
    """Everything the screen shows. `pending` is the update or way back that waits for the confirmation ({"action", "component"}), `failure` the kind of the last
    failed read ("" : none)."""
    is_running = running(job)
    allowed = can_apply(apply_on, status, is_running)
    rows = [item_row(item, allowed) for item in status["items"]] if status is not None else []
    pending_item = next((item for item in status["items"] if pending and item["id"] == pending["component"]), None) if status is not None else None
    confirm = confirm_text(pending["action"], pending_item) if pending and pending_item else ""
    return {
        "title": _("SELFUPD_TITLE"),
        "intro": _("SELFUPD_INTRO"),
        "switchText": _("SELFUPD_SWITCH_TITLE"),
        "switchHint": _("SELFUPD_SWITCH_HINT"),
        "applyOn": bool(apply_on),
        "failure": read_failure_text(failure) if failure else "",
        "loaded": status is not None,
        "rows": rows,
        "mode": mode_text(apply_on, status) if status is not None else "",
        "columns": [_("SELFUPD_COL_PROGRAM"), _("SELFUPD_COL_INSTALLED"), _("SELFUPD_COL_PREVIOUS"), _("SELFUPD_COL_LATEST"), _("SELFUPD_COL_STATE")],
        "checkLabel": _("SELFUPD_CHECK"),
        "updateLabel": _("SELFUPD_UPDATE"),
        "goBackLabel": _("SELFUPD_ROLLBACK"),
        "canCheck": not busy and not is_running,
        "confirm": confirm,
        "confirmTitle": _("SELFUPD_CONFIRM_TITLE"),
        "confirmNote": _("SELFUPD_CONFIRM_NOTE"),
        "confirmYes": _("COMMON_CONFIRM"),
        "confirmNo": _("COMMON_CANCEL"),
        "message": message,
        "job": job_view(job, silent, gave_up),
    }


EMPTY_VIEW: dict = {"title": "", "intro": "", "switchText": "", "switchHint": "", "applyOn": False, "failure": "", "loaded": False, "rows": [], "mode": "", "columns": [],
                    "checkLabel": "", "updateLabel": "", "goBackLabel": "", "canCheck": False, "confirm": "", "confirmTitle": "", "confirmNote": "", "confirmYes": "",
                    "confirmNo": "", "message": "", "job": {}}
