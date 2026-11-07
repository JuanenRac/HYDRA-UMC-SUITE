# =============================================================================
# HYDRA-UMC SUITE - panel_logic/setup_screens.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The Setup screens without any window toolkit: the installed versions, the first-run checklist, the sign-in security, the remote
# access setup, the state of the push notifications and the history. They read the same routes as the
# configuration tabs of HYDRA-UMC STUDIO and follow the same rules: what could not be read is "not known" and never "to do"; nothing
# is changed unless a person turns it on; the signing key is rotated only after a switch that is off every time the screen opens and
# a confirmation; "close all" is the conservative way out and asks first. Every view is a plain dict with its sentences already in
# the language of the interface, so the one generic screen of the interface only draws it.
# =============================================================================
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from hydra_suite.i18n import _
from hydra_suite.nav_items import SETUP_ITEMS

#: The screens, in the order of the menu: (language key of the label, key of the panel); the navigation owns the list.
SCREENS = SETUP_ITEMS
SCREEN_KEYS = frozenset(key for _label, key in SCREENS)

#: The kinds of app the server lets find it (settings.remoteAccess), in the order they are shown.
REMOTE_CLIENTS = ("suite", "android", "ios", "watch", "dsi")
#: The events the server announces that this program names; any other is shown by its own id.
KNOWN_EVENTS = ("jobFinished", "globalStop", "operatorHeartbeatLost")


# -- Reading ----------------------------------------------------------------------------------------------------------------------

def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _seconds(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 and value == value else None


def failure_text(result: tuple[int, object] | None) -> str:
    """"" when the answer was read; otherwise why it could not be, as a sentence."""
    if result is None:
        return _("SETUP_ERROR_NETWORK")
    status = result[0]
    if status == 200:
        return ""
    if status == 404:
        return _("SETUP_ERROR_UNSUPPORTED")
    if status in (401, 403):
        return _("SETUP_ERROR_FORBIDDEN")
    return _("SETUP_ERROR_HTTP")


def parse_server_info(body: object) -> dict | None:
    """The server about itself (GET /api/hydra-info); None when the answer is not an object."""
    if not isinstance(body, dict):
        return None
    api = body.get("remoteApiVersion")
    return {
        "appVersion": _text(body.get("appVersion")),
        "remoteApiVersion": api if isinstance(api, int) and not isinstance(api, bool) else None,
        "hostname": _text(body.get("hostname")),
        "controllerCount": _count(body.get("controllerCount")),
        "robotCount": _count(body.get("robotCount")),
        "uptimeSeconds": _count(body.get("uptimeSeconds")),
    }


def parse_installed(projects: object) -> list[dict]:
    """The programs of the scan (GET /api/ecosystem/status), those with a name only, in alphabetical order."""
    if not isinstance(projects, list):
        return []
    out = [
        {"name": name, "family": _text(item.get("family")), "version": _text(item.get("version"))}
        for item in projects
        if isinstance(item, dict) and (name := _text(item.get("name"))) is not None
    ]
    return sorted(out, key=lambda item: item["name"].lower())


def uptime_text(seconds: int) -> str:
    """"3 d 4 h", "5 h 12 min", "8 min": how long the server has been running."""
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days > 0:
        return f"{days} d {hours} h"
    if hours > 0:
        return f"{hours} h {minutes} min"
    return f"{minutes} min"


def date_text(unix_seconds: int) -> str:
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") + " UTC"


def _view(title_key: str, intro_key: str) -> dict:
    """The empty view: every part the generic screen can draw, so a missing part is simply not drawn."""
    return {
        "title": _(title_key), "intro": _(intro_key), "error": "", "notice": "", "noticeOk": True,
        "facts": [], "checks": [], "headers": [], "rows": [], "toggles": [], "buttons": [], "parts": [],
        "qr": None, "note": "", "summary": "", "section": "", "extraRows": [], "extraHeaders": [], "extraTitle": "",
    }


def empty_view(title_key: str, intro_key: str) -> dict:
    """The empty view of a screen that is not one of the Setup readings (the Help by level)."""
    return _view(title_key, intro_key)


def no_server_view(key: str, message: str) -> dict:
    """The screen of a Setup entry while no server is active: its title and why there is nothing to show."""
    label = next((label for label, panel in SCREENS if panel == key), "")
    view = _view(label, label) if label else _view("SETUP_UNKNOWN", "SETUP_UNKNOWN")
    view["intro"], view["error"] = "", message
    return view


# -- Installed versions -----------------------------------------------------------------------------------------------------------

def versions_view(suite_version: str, info: dict | None, projects: list[dict], failure: str) -> dict:
    view = _view("SETUP_VERSIONS_TITLE", "SETUP_VERSIONS_INTRO")
    view["error"] = failure
    unknown = _("SETUP_UNKNOWN")
    view["facts"] = [{"label": _("SETUP_VERSIONS_SUITE"), "value": suite_version}]
    if info is not None:
        view["facts"] += [
            {"label": _("SETUP_VERSIONS_SERVER"), "value": info["appVersion"] or unknown},
            {"label": _("SETUP_VERSIONS_UPTIME"), "value": uptime_text(info["uptimeSeconds"])},
        ]
    view["section"] = _("SETUP_VERSIONS_PROGRAMS")
    view["headers"] = [_("SETUP_VERSIONS_COL_PROGRAM"), _("SETUP_VERSIONS_COL_FAMILY"), _("SETUP_VERSIONS_COL_INSTALLED")]
    view["rows"] = [[p["name"], p["family"] or "-", p["version"] or _("SETUP_VERSIONS_NO_VERSION")] for p in projects]
    if not projects:
        view["summary"] = _("SETUP_VERSIONS_NONE")
    else:
        view["summary"] = _("SETUP_VERSIONS_COUNT", with_version=sum(1 for p in projects if p["version"]), total=len(projects))
    view["note"] = _("SETUP_VERSIONS_NO_SOURCE")
    view["buttons"] = [{"id": "refresh", "label": _("SETUP_REFRESH"), "enabled": True, "danger": False, "confirm": ""}]
    return view


# -- First-run checklist ----------------------------------------------------------------------------------------------------------

def install_steps(info: dict | None, second_factor: bool | None) -> list[dict]:
    """The steps in the order they are done. A step whose answer is not known (the server could not be read) is "unknown", never "todo"."""
    def done(flag: bool) -> str:
        return "done" if flag else "todo"

    return [
        {"id": "server", "state": done(info is not None), "count": None},
        {"id": "controller", "state": done(info["controllerCount"] > 0) if info else "unknown", "count": info["controllerCount"] if info else 0},
        {"id": "robot", "state": done(info["robotCount"] > 0) if info else "unknown", "count": info["robotCount"] if info else 0},
        {"id": "second_factor", "state": "unknown" if second_factor is None else done(second_factor), "count": None},
    ]


def next_step(steps: list[dict]) -> dict | None:
    return next((step for step in steps if step["state"] == "todo"), None)


def installation_view(info: dict | None, second_factor: bool | None, failure: str) -> dict:
    view = _view("SETUP_INSTALLATION_TITLE", "SETUP_INSTALLATION_INTRO")
    view["error"] = failure
    steps = install_steps(info, second_factor)
    if info is not None:
        view["facts"] = [
            {"label": _("SETUP_INSTALLATION_HOST"), "value": info["hostname"] or "-"},
            {"label": _("SETUP_INSTALLATION_VERSION"), "value": info["appVersion"] or "-"},
            {"label": _("SETUP_INSTALLATION_UPTIME"), "value": uptime_text(info["uptimeSeconds"])},
        ]
    view["checks"] = [
        {
            "id": step["id"],
            "state": step["state"],
            "label": _("SETUP_INSTALLATION_STEP_" + step["id"].upper()) + (f" ({step['count']})" if step["count"] is not None and step["state"] != "unknown" else ""),
            "hint": _("SETUP_INSTALLATION_STEP_" + step["id"].upper() + "_HINT"),
        }
        for step in steps
    ]
    view["summary"] = _("SETUP_INSTALLATION_PROGRESS", done=sum(1 for s in steps if s["state"] == "done"), total=len(steps))
    following = next_step(steps)
    if following is not None:
        view["section"] = _("SETUP_INSTALLATION_NEXT", step=_("SETUP_INSTALLATION_STEP_" + following["id"].upper()))
    elif all(step["state"] == "done" for step in steps):
        view["section"] = _("SETUP_INSTALLATION_ALL_DONE")
    else:
        view["section"] = _("SETUP_INSTALLATION_CANNOT_TELL")
    view["note"] = _("SETUP_INSTALLATION_NO_INSTALLER")
    view["buttons"] = [{"id": "refresh", "label": _("SETUP_REFRESH"), "enabled": True, "danger": False, "confirm": ""}]
    return view


# -- Sign-in security -------------------------------------------------------------------------------------------------------------

def parse_keys(body: object) -> dict | None:
    """The public state of the token signing keys (GET /api/admin/jwt-keys): never more than the name and the dates of each key."""
    if not isinstance(body, dict):
        return None
    keys = []
    for item in body.get("keys") if isinstance(body.get("keys"), list) else []:
        if not isinstance(item, dict) or _text(item.get("kid")) is None or _seconds(item.get("createdAt")) is None:
            continue
        keys.append({
            "kid": _text(item.get("kid")), "createdAt": _seconds(item.get("createdAt")), "retiredAt": _seconds(item.get("retiredAt")),
            "active": item.get("active") is True, "acceptedUntil": _seconds(item.get("acceptedUntil")),
        })
    return {"algorithm": _text(body.get("algorithm")), "keys": keys}


def active_key(keys: list[dict]) -> dict | None:
    """The newest key that is not retired."""
    return max((key for key in keys if key["active"]), key=lambda key: key["createdAt"], default=None)


def security_checks(second_factor: bool | None, algorithm: str | None) -> list[dict]:
    """Each check is true, false, or None when the answer is not known (the server did not say)."""
    return [
        {"id": "second_factor", "ok": second_factor},
        {"id": "asymmetric_keys", "ok": None if algorithm is None else algorithm == "EdDSA"},
    ]


def rotate_failure_text(result: tuple[int, object] | None) -> str:
    """Why a rotation did not happen, in the codes of the server."""
    if result is None:
        return _("SETUP_ERROR_NETWORK")
    status = result[0]
    if status == 404:
        return _("SETUP_ERROR_UNSUPPORTED")
    if status in (401, 403):
        return _("SETUP_ERROR_FORBIDDEN")
    if status == 409:
        return _("SETUP_SECURITY_ERROR_ASYMMETRIC_OFF")
    if status == 500:
        return _("SETUP_SECURITY_ERROR_FILE")
    return _("SETUP_ERROR_HTTP")


def security_view(second_factor: bool | None, keys: dict | None, is_admin: bool, failure: str, allow_rotation: bool, notice: str, notice_ok: bool) -> dict:
    view = _view("SETUP_SECURITY_TITLE", "SETUP_SECURITY_INTRO")
    view["error"] = failure
    view["notice"], view["noticeOk"] = notice, notice_ok
    view["checks"] = [
        {
            "id": check["id"],
            "state": "unknown" if check["ok"] is None else "done" if check["ok"] else "warn",
            "label": _("SETUP_SECURITY_CHECK_" + check["id"].upper()),
            "hint": "",
        }
        for check in security_checks(second_factor, keys["algorithm"] if keys else None)
    ]
    view["summary"] = _("SETUP_SECURITY_TOTP_WHERE")
    if not is_admin:
        view["note"] = _("SETUP_SECURITY_ADMIN_ONLY")
        return view
    view["section"] = _("SETUP_SECURITY_KEYS_TITLE")
    if keys is not None:
        current = active_key(keys["keys"])
        view["facts"] = [{"label": _("SETUP_SECURITY_ALGORITHM"), "value": keys["algorithm"] or "-"}]
        if current is not None:
            view["facts"].append({"label": _("SETUP_SECURITY_ACTIVE_KEY"), "value": current["kid"]})
        view["headers"] = [_("SETUP_SECURITY_COL_KEY"), _("SETUP_SECURITY_COL_CREATED"), _("SETUP_SECURITY_COL_STATE")]
        view["rows"] = [
            [
                key["kid"], date_text(key["createdAt"]),
                _("SETUP_SECURITY_KEY_ACTIVE") if key["active"]
                else _("SETUP_SECURITY_KEY_RETIRED", date=date_text(key["acceptedUntil"])) if key["acceptedUntil"] is not None
                else _("SETUP_SECURITY_KEY_RETIRED_PLAIN"),
            ]
            for key in keys["keys"]
        ]
        view["note"] = _("SETUP_SECURITY_KEYS_INTRO")
        view["toggles"] = [{"id": "allow_rotation", "label": _("SETUP_SECURITY_ALLOW_ROTATION"), "checked": allow_rotation, "enabled": True}]
        view["buttons"] = [
            {"id": "rotate", "label": _("SETUP_SECURITY_ROTATE"), "enabled": allow_rotation, "danger": True, "confirm": _("SETUP_SECURITY_ROTATE_CONFIRM")},
            {"id": "refresh", "label": _("SETUP_REFRESH"), "enabled": True, "danger": False, "confirm": ""},
        ]
    else:
        view["buttons"] = [{"id": "refresh", "label": _("SETUP_REFRESH"), "enabled": True, "danger": False, "confirm": ""}]
    return view


# -- Remote access ----------------------------------------------------------------------------------------------------------------

def client_allowed(setting: object, client: str) -> bool:
    """Whether the server lets this kind of app find it: its own choice, else the old combined switch, else allowed (as the server decides it)."""
    if not isinstance(setting, dict):
        return True
    own = setting.get(client)
    if isinstance(own, bool):
        return own
    combined = setting.get("enabled")
    return combined if isinstance(combined, bool) else True


def allowed_clients(setting: object) -> list[str]:
    return [client for client in REMOTE_CLIENTS if client_allowed(setting, client)]


def with_client(setting: object, client: str, allowed: bool) -> dict:
    """The setting with one kind of app changed."""
    updated = dict(setting) if isinstance(setting, dict) else {}
    if client in REMOTE_CLIENTS:
        updated[client] = bool(allowed)
    return updated


def close_all_setting(setting: object) -> dict:
    """The setting that closes the access of every kind of app at once (the conservative way out)."""
    closed = dict(setting) if isinstance(setting, dict) else {}
    for client in REMOTE_CLIENTS:
        closed[client] = False
    return closed


def address_reachable_from_outside(address: str) -> bool:
    """A server the apps reach as localhost cannot be reached from a phone."""
    try:
        host = urlparse(address).hostname
    except ValueError:
        return False
    return bool(host) and host not in ("localhost", "127.0.0.1", "::1")


def remote_view(address: str, setting: object, qr: dict | None, can_change: bool) -> dict:
    view = _view("SETUP_REMOTE_TITLE", "SETUP_REMOTE_INTRO")
    view["section"] = _("SETUP_REMOTE_STEP1")
    view["facts"] = [{"label": _("SETUP_REMOTE_ADDRESS"), "value": address or "-"}]
    view["qr"] = qr
    if address and not address_reachable_from_outside(address):
        view["error"] = _("SETUP_REMOTE_LOCAL_WARNING")
    view["extraTitle"] = _("SETUP_REMOTE_STEP2")
    view["summary"] = _("SETUP_REMOTE_STEP2_HINT")
    view["toggles"] = [
        {"id": "client_" + client, "label": _("SETUP_REMOTE_CLIENT_" + client.upper()), "checked": client_allowed(setting, client), "enabled": can_change}
        for client in REMOTE_CLIENTS
    ]
    open_count = len(allowed_clients(setting))
    view["extraRows"] = [[_("SETUP_REMOTE_OPEN_COUNT", open=open_count, total=len(REMOTE_CLIENTS))]]
    view["buttons"] = [{"id": "close_all", "label": _("SETUP_REMOTE_CLOSE_ALL"), "enabled": can_change and open_count > 0, "danger": True, "confirm": _("SETUP_REMOTE_CLOSE_ALL_CONFIRM")}]
    view["note"] = _("SETUP_REMOTE_STEP1_HINT") + "\n\n" + _("SETUP_REMOTE_STEP3") + ": " + _("SETUP_REMOTE_STEP3_HINT")
    return view


# -- Push notifications -----------------------------------------------------------------------------------------------------------

def parse_push(body: object) -> dict | None:
    """The state of the push notifications (GET /api/admin/push); it never carries the credentials or the device tokens."""
    if not isinstance(body, dict):
        return None
    events = body.get("events")
    pairs = sorted(((str(k), v) for k, v in events.items() if isinstance(v, bool)), key=lambda pair: pair[0]) if isinstance(events, dict) else []
    return {
        "enabled": body.get("enabled") is True, "configured": body.get("configured") is True, "problem": _text(body.get("problem")),
        "devices": _count(body.get("devices")), "sandbox": body.get("sandbox") is True, "events": [{"id": k, "on": v} for k, v in pairs],
    }


def push_verdict(state: dict) -> str:
    """What the state means for a person: off, on but unable to send, or sending."""
    if not state["enabled"]:
        return "off"
    return "ready" if state["configured"] else "needs_credentials"


def event_label(event_id: str) -> str:
    return _("SETUP_NOTIFICATIONS_EVENT_" + event_id.upper()) if event_id in KNOWN_EVENTS else event_id


def notifications_view(state: dict | None, is_admin: bool, failure: str) -> dict:
    view = _view("SETUP_NOTIFICATIONS_TITLE", "SETUP_NOTIFICATIONS_INTRO")
    view["buttons"] = [{"id": "refresh", "label": _("SETUP_REFRESH"), "enabled": True, "danger": False, "confirm": ""}]
    if not is_admin:
        view["note"] = _("SETUP_NOTIFICATIONS_ADMIN_ONLY")
        view["buttons"] = []
        return view
    view["error"] = failure
    if state is None:
        return view
    verdict = push_verdict(state)
    view["section"] = _("SETUP_NOTIFICATIONS_VERDICT_" + verdict.upper())
    facts = []
    if state["problem"] and verdict != "ready":
        facts.append({"label": _("SETUP_NOTIFICATIONS_PROBLEM_LABEL"), "value": state["problem"]})
    facts.append({"label": _("SETUP_NOTIFICATIONS_DEVICES_LABEL"), "value": str(state["devices"])})
    if state["sandbox"]:
        facts.append({"label": _("SETUP_NOTIFICATIONS_SANDBOX_LABEL"), "value": _("SETUP_NOTIFICATIONS_SANDBOX")})
    view["facts"] = facts
    view["checks"] = [
        {"id": event["id"], "state": "done" if event["on"] else "unknown", "label": event_label(event["id"]), "hint": _("SETUP_ON") if event["on"] else _("SETUP_OFF")}
        for event in state["events"]
    ]
    view["note"] = _("SETUP_NOTIFICATIONS_READ_ONLY")
    return view


# -- History ----------------------------------------------------------------------------------------------------------------------

def history_parts(is_admin: bool) -> list[str]:
    return ["connections", "audit"] if is_admin else ["connections"]


def history_view(part: str, is_admin: bool, clients: list[dict], events: list[dict], audit: list[dict], failure: str) -> dict:
    """`clients`, `events` and `audit` are the rows the connection history and the audit record screens already build."""
    view = _view("SETUP_HISTORY_TITLE", "SETUP_HISTORY_INTRO")
    view["error"] = failure
    parts = history_parts(is_admin)
    part = part if part in parts else "connections"
    view["parts"] = [{"id": item, "label": _("SETUP_HISTORY_PART_" + item.upper()), "selected": item == part} for item in parts]
    if part == "connections":
        view["headers"] = [_("SETUP_HISTORY_COL_WHO"), _("SETUP_HISTORY_COL_DETAIL"), _("SETUP_HISTORY_COL_SESSIONS"), _("SETUP_HISTORY_COL_LOGINS"), _("SETUP_HISTORY_COL_LAST_SEEN")]
        view["rows"] = [[c["who"], c["detail"], c["sessions"], c["logins"], c["lastSeen"]] for c in clients]
        view["extraTitle"] = _("SETUP_HISTORY_EVENTS")
        view["extraHeaders"] = [_("SETUP_HISTORY_COL_EVENT"), _("SETUP_HISTORY_COL_WHEN")]
        view["extraRows"] = [[str(e["action"]) + str(e["detail"]), e["ago"]] for e in events]
    else:
        view["headers"] = [_("SETUP_HISTORY_COL_TIME"), _("SETUP_HISTORY_COL_TYPE"), _("SETUP_HISTORY_COL_OUTCOME"), _("SETUP_HISTORY_COL_ACCOUNT"), _("SETUP_HISTORY_COL_ROBOT")]
        view["rows"] = [[a["time"], a["type"], a["outcome"], a["account"], a["robot"]] for a in audit]
    if not is_admin:
        view["note"] = _("SETUP_HISTORY_AUDIT_ADMIN_ONLY")
    view["buttons"] = [{"id": "refresh", "label": _("SETUP_REFRESH"), "enabled": True, "danger": False, "confirm": ""}]
    return view
