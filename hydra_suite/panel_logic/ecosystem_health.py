# =============================================================================
# HYDRA-UMC SUITE - panel_logic/ecosystem_health.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The health of the services of the ecosystem, read from GET /api/ecosystem/health without any window toolkit: one card per service
# (state, why, the version it reports against the version expected, how long since it last answered), the filters by state and by
# version drift, and the notices for a TLS certificate about to expire, a service that is down or degraded and a version that differs
# from its manifest. Reading is tolerant: a server that predates the route (or where an administrator did not turn it on) answers 404
# and the screen says so; a damaged entry is dropped, not the rest; a state this app does not know is shown as unknown. The server
# only sends the port, health path and unit of a service to an administrator, and nothing here reads them, so a card never shows one.
# =============================================================================
from __future__ import annotations

from datetime import datetime, timezone

from hydra_suite.i18n import _

SERVICE_STATES = ("ok", "degraded", "down", "unknown")
SERVICE_REASONS = (
    "health_ok", "health_degraded", "health_failed", "http_error", "unreachable", "unreachable_unit_active", "reachable_unit_not_active",
    "unit_active", "unit_starting", "unit_failed", "unit_inactive", "no_signal", "probe_error",
)
CERTIFICATE_STATES = ("ok", "expiring", "expired", "unreadable")
WARNING_CODES = ("certificate_expiring", "certificate_expired", "certificate_unreadable", "version_drift", "service_down", "service_degraded")
#: The filters of the screen, in the order they are offered.
FILTERS = ("all", *SERVICE_STATES, "drift")
POLL_MS = 15000  # how often the screen asks again while it is on screen
#: The most serious state first, so what needs attention is at the top.
SEVERITY = {"down": 0, "degraded": 1, "unknown": 2, "ok": 3}


def _text(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) and value.strip() else ""


def _whole(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        then = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return then if then.tzinfo else then.replace(tzinfo=timezone.utc)


def ago(iso: object, now: datetime | None = None) -> str:
    """"5s", "12m", "3h 4m", "2d" since a date, short enough for a card; "" when there is no usable date."""
    then = _date(iso)
    if then is None:
        return ""
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


def parse_service(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = _text(raw.get("name"), 80)
    if not name:
        return None
    state = raw.get("state")
    reason = raw.get("reason")
    return {
        "name": name,
        # a state this app does not know (a newer server) is shown as unknown rather than dropped
        "state": state if isinstance(state, str) and state in SERVICE_STATES else "unknown",
        "reason": reason if isinstance(reason, str) and reason in SERVICE_REASONS else "",
        "versionExpected": _text(raw.get("version_expected"), 24),
        "versionReported": _text(raw.get("version_reported"), 24),
        "drift": raw.get("drift") is True,
        "lastSeen": raw.get("last_seen_utc") if _date(raw.get("last_seen_utc")) is not None else "",
        "latencyMs": _whole(raw.get("latency_ms")),
    }


def parse_certificate(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    state = raw.get("state")
    if not isinstance(state, str) or state not in CERTIFICATE_STATES:
        return None
    not_after = raw.get("not_after_utc")
    warn = _whole(raw.get("warn_days"))
    return {
        "state": state,
        "notAfter": not_after if _date(not_after) is not None else "",
        "daysLeft": _whole(raw.get("days_left")),
        "warnDays": warn if warn is not None else 30,
    }


def parse_warning(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    code = raw.get("code")
    if not isinstance(code, str) or code not in WARNING_CODES:
        return None
    return {"code": code, "service": _text(raw.get("service"), 80)}


def parse_health(body: object) -> dict | None:
    """The answer of the route; None when it is not the shape of the route at all."""
    if not isinstance(body, dict) or body.get("schema_version") != "1.0" or not isinstance(body.get("services"), list):
        return None
    services = [s for s in (parse_service(i) for i in body["services"]) if s is not None]
    warnings = body.get("warnings")
    return {
        "available": body.get("available") is not False,
        "services": services,
        "certificate": parse_certificate(body.get("certificate")),
        "warnings": [w for w in (parse_warning(i) for i in warnings) if w is not None] if isinstance(warnings, list) else [],
    }


def summary(services: list[dict]) -> dict:
    """The counts, taken from the list itself so the cards and the numbers can never disagree."""
    counts = {state: sum(1 for s in services if s["state"] == state) for state in SERVICE_STATES}
    return {"all": len(services), **counts, "drift": sum(1 for s in services if s["drift"])}


def filter_services(services: list[dict], selected: str) -> list[dict]:
    """The services a filter keeps: one state, or only those that report another version than their manifest."""
    if selected == "drift":
        return [s for s in services if s["drift"]]
    if selected in SERVICE_STATES:
        return [s for s in services if s["state"] == selected]
    return list(services)


def sort_by_severity(services: list[dict]) -> list[dict]:
    return sorted(services, key=lambda s: (SEVERITY[s["state"]], s["name"].lower()))


def status_for(result: tuple[int, object] | None) -> str:
    """"" when the answer can be read; otherwise the sentence for the problem (no route, not allowed, or anything else)."""
    if result is None:
        return _("ECOHEALTH_LOAD_ERROR")
    status = result[0]
    if status == 200:
        return "" if parse_health(result[1]) is not None else _("ECOHEALTH_LOAD_ERROR")
    if status == 404:
        return _("ECOHEALTH_UNSUPPORTED")
    if status in (401, 403):
        return _("ECOHEALTH_FORBIDDEN")
    return _("ECOHEALTH_LOAD_ERROR")


def filter_rows(services: list[dict], selected: str) -> list[dict]:
    counts = summary(services)
    return [{"key": f, "label": f"{_('ECOHEALTH_FILTER_' + f.upper())} ({counts[f]})", "selected": f == selected} for f in FILTERS]


def card_rows(services: list[dict], selected: str, now: datetime | None = None) -> list[dict]:
    rows = []
    for s in sort_by_severity(filter_services(services, selected)):
        heard = ago(s["lastSeen"], now)
        unknown = _("ECOHEALTH_VERSION_UNKNOWN")
        seen = _("ECOHEALTH_LAST_SEEN", ago=heard) if heard else _("ECOHEALTH_NEVER_SEEN")
        if s["latencyMs"] is not None:
            seen += " - " + _("ECOHEALTH_LATENCY", ms=s["latencyMs"])
        rows.append(
            {
                "name": s["name"],
                "state": s["state"],
                "stateLabel": _("ECOHEALTH_STATE_" + s["state"].upper()),
                "reason": _("ECOHEALTH_REASON_" + s["reason"].upper()) if s["reason"] else "",
                "versions": f"{_('ECOHEALTH_VERSION_EXPECTED')}: {s['versionExpected'] or unknown} - {_('ECOHEALTH_VERSION_REPORTED')}: {s['versionReported'] or unknown}",
                "drift": s["drift"],
                "driftLabel": _("ECOHEALTH_DRIFT_BADGE") if s["drift"] else "",
                "seen": seen,
            }
        )
    return rows


def notice_rows(health: dict) -> list[dict]:
    """The sentences above the cards: the certificate first, then the warnings of the server (its certificate ones are the same
    sentence as the certificate line, so they are not repeated). level is "ok", "warn" or "error"."""
    rows = []
    cert = health.get("certificate")
    if cert is not None:
        level = "ok" if cert["state"] == "ok" else "warn" if cert["state"] == "expiring" else "error"
        days = cert["daysLeft"] if cert["daysLeft"] is not None else 0
        rows.append({"level": level, "text": _("ECOHEALTH_CERT_" + cert["state"].upper(), days=days, date=cert["notAfter"][:10])})
    days = cert["daysLeft"] if cert is not None and cert["daysLeft"] is not None else 0
    for w in health.get("warnings", []):
        if w["code"].startswith("certificate_"):
            continue
        rows.append({"level": "error" if w["code"] == "service_down" else "warn", "text": _("ECOHEALTH_WARNING_" + w["code"].upper(), service=w["service"], days=days)})
    return rows
