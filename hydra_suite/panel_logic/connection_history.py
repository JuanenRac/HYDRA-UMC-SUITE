# =============================================================================
# HYDRA-UMC SUITE - panel_logic/connection_history.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# A simple view of who has connected to the server: the clients it has seen and the latest sign-ins and sign-outs, read from
# GET /api/connections/clients and /api/connections/events without any window toolkit. Reading is tolerant: a server that
# predates the routes answers 404 and the screen says so; a damaged entry is dropped, not the rest. The answers hold no
# password, token or cookie; the address and user agent only come for an administrator when the server keeps them.
# =============================================================================
from __future__ import annotations

import re
from datetime import datetime, timezone

from hydra_suite.i18n import _

CLIENT_KINDS = ("studio", "suite", "android", "ios", "dsi", "watch", "voice", "other")
ACTIONS = ("first_seen", "login", "login_failed", "second_factor_failed", "logout", "session_ended", "session_expired")
FAILURES = ("login_failed", "second_factor_failed")


def _text(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) and value.strip() else ""


def _whole(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        then = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return then if then.tzinfo else then.replace(tzinfo=timezone.utc)


def _kind(value: object) -> str:
    return value if isinstance(value, str) and value in CLIENT_KINDS else "other"


def _origin(value: object) -> str:
    return value if value in ("local", "remote") else ""


def ago(iso: object, now: datetime | None = None) -> str:
    """"5s", "12m", "3h 4m", "2d" since a date, short enough for a table cell."""
    then = _date(iso)
    if then is None:
        return "-"
    seconds = max(0, int(((now or datetime.now(timezone.utc)) - then).total_seconds()))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h {minutes % 60}m"
    return f"{hours // 24}d"


def parse_client(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    client_id = raw.get("id")
    first, last = _date(raw.get("first_seen_utc")), _date(raw.get("last_seen_utc"))
    if not isinstance(client_id, str) or not re.fullmatch(r"[0-9a-f]{16}", client_id) or first is None or last is None:
        return None
    return {
        "id": client_id,
        "kind": _kind(raw.get("kind")),
        "user": _text(raw.get("user"), 60),
        "appVersion": _text(raw.get("app_version"), 24),
        "origin": _origin(raw.get("origin")),
        "twoFactor": raw.get("two_factor") is True,
        "lastSeen": raw.get("last_seen_utc"),
        "activeSessions": _whole(raw.get("active_sessions")),
        "loginsOk": _whole(raw.get("logins_ok")),
        "loginsFailed": _whole(raw.get("logins_failed")),
        "ip": _text(raw.get("ip"), 64),
        "agent": _text(raw.get("agent"), 120),
    }


def parse_event(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    event_id, action = raw.get("id"), raw.get("action")
    if not isinstance(event_id, int) or isinstance(event_id, bool) or event_id < 1 or _date(raw.get("at_utc")) is None:
        return None
    if not isinstance(raw.get("client_id"), str) or not isinstance(action, str) or action not in ACTIONS:
        return None
    return {
        "id": event_id,
        "at": raw.get("at_utc"),
        "action": action,
        "kind": _kind(raw.get("client_kind")),
        "user": _text(raw.get("user"), 60),
        "appVersion": _text(raw.get("app_version"), 24),
        "ip": _text(raw.get("ip"), 64),
    }


def parse_clients(body: object) -> list[dict]:
    items = body.get("clients") if isinstance(body, dict) else None
    return [c for c in (parse_client(i) for i in items) if c is not None] if isinstance(items, list) else []


def parse_events(body: object) -> list[dict]:
    items = body.get("events") if isinstance(body, dict) else None
    return [e for e in (parse_event(i) for i in items) if e is not None] if isinstance(items, list) else []


def status_for(result: tuple[int, object] | None) -> str:
    """"" when the answer can be read; otherwise the sentence for the problem (no route yet, not allowed, or anything else)."""
    if result is None:
        return _("CONNECTIONS_LOAD_ERROR")
    status = result[0]
    if status == 200:
        return ""
    if status == 404:
        return _("CONNECTIONS_UNSUPPORTED")
    if status in (401, 403):
        return _("CONNECTIONS_FORBIDDEN")
    return _("CONNECTIONS_LOAD_ERROR")


def client_rows(clients: list[dict], now: datetime | None = None) -> list[dict]:
    rows = []
    for c in clients:
        who = c["user"] or _("CONNECTIONS_NO_USER")
        kind = _("CONNECTIONS_KIND_" + c["kind"].upper()) + (f" {c['appVersion']}" if c["appVersion"] else "")
        if c["origin"]:
            kind += " - " + _("CONNECTIONS_ORIGIN_" + c["origin"].upper())
        if c["ip"]:
            kind += f" - {c['ip']}"
        rows.append(
            {
                "who": who,
                "detail": kind,
                "twoFactor": c["twoFactor"],
                "active": c["activeSessions"] > 0,
                "sessions": _("CONNECTIONS_SESSIONS", open=c["activeSessions"]),
                "logins": _("CONNECTIONS_LOGINS", ok=c["loginsOk"], failed=c["loginsFailed"]),
                "lastSeen": ago(c["lastSeen"], now),
            }
        )
    return rows


def event_rows(events: list[dict], now: datetime | None = None) -> list[dict]:
    rows = []
    for e in events:
        who = e["user"] or _("CONNECTIONS_NO_USER")
        kind = _("CONNECTIONS_KIND_" + e["kind"].upper()) + (f" {e['appVersion']}" if e["appVersion"] else "")
        rows.append(
            {
                "action": _("CONNECTIONS_ACTION_" + e["action"].upper()),
                "detail": f" - {who} ({kind})",
                "failure": e["action"] in FAILURES,
                "ago": ago(e["at"], now),
            }
        )
    return rows
