# =============================================================================
# HYDRA-UMC SUITE - panel_logic/ops_proposals.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The proposals of the node watchdog (OPS-AGENT) that wait for a person. They go through the server (GET /api/ops-agent/proposals and
# POST /api/ops-agent/proposals/decide), which speaks to the watchdog over its signed channel; the watchdog keeps the proposals and the last
# word. Approving carries confirm: true, rejecting does not; the person who decides is the signed-in account, which the server names, so no
# name is sent from here. Read without any window toolkit; a server without the route (404) or without the channel set up (503, available
# false) is told apart from an account that may not use it (401/403) and from a proposal that is no longer pending (404 with a code).
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _

DECISIONS = ("approved", "rejected")


def _text(value: object) -> str:
    return value[:500] if isinstance(value, str) else ""


def parse_lists(body: object) -> dict | None:
    """The pending and decided lists in an answer of the route; None when the answer holds no pending list. Entries that are not entries are dropped."""
    if not isinstance(body, dict) or not isinstance(body.get("pending"), list):
        return None
    pending = []
    for item in body["pending"]:
        entry = item if isinstance(item, dict) else {}
        incident = entry.get("incident") if isinstance(entry.get("incident"), dict) else {}
        incident_id = _text(incident.get("incidentId"))
        if not incident_id:
            continue
        pending.append({
            "incidentId": incident_id, "sourceNode": _text(incident.get("sourceNode")), "detectedAt": _text(incident.get("detectedAt")),
            "severity": _text(incident.get("severity")), "component": _text(incident.get("component")), "symptom": _text(incident.get("symptom")),
        })
    decided = []
    for item in body["decided"] if isinstance(body.get("decided"), list) else []:
        entry = item if isinstance(item, dict) else {}
        incident_id = _text(entry.get("incidentId"))
        if incident_id and entry.get("decision") in DECISIONS:
            decided.append({"incidentId": incident_id, "decision": entry["decision"], "by": _text(entry.get("by")), "decidedAt": _text(entry.get("decidedAt"))})
    return {"pending": pending, "decided": decided}


def body_for(incident_id: str, decision: str) -> dict:
    """The body of a decision. Approving carries confirm: true; rejecting never does."""
    body = {"incidentId": incident_id, "decision": decision}
    if decision == "approved":
        body["confirm"] = True
    return body


def needs_confirmation(decision: str) -> bool:
    """Approving opens the incident for the maintenance work, so it is the decision that is confirmed on screen."""
    return decision == "approved"


def hidden_for(result: tuple[int, object] | None) -> bool:
    """True when the server has no channel to the watchdog (no route, or not configured): the section stays out of the way."""
    if result is None:
        return False
    status, body = result
    if status == 404:
        return not (isinstance(body, dict) and body.get("code") == "operation-failed")
    return status == 503 and isinstance(body, dict) and body.get("available") is False


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading or decision, empty when it worked."""
    if result is None:
        return _("OPSPROP_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("OPSPROP_FORBIDDEN")
    if status == 404 and isinstance(body, dict) and body.get("code") == "operation-failed":
        return _("OPSPROP_NOT_PENDING")
    if status == 200 and isinstance(body, dict):
        return ""
    detail = ""
    if isinstance(body, dict):
        for key in ("reason", "error"):
            if isinstance(body.get(key), str):
                detail = body[key]
                break
    if status >= 300 and detail:
        return _("OPSPROP_DECIDE_ERROR", reason=detail[:300])
    return _("OPSPROP_LOAD_ERROR")


def decision_ok(result: tuple[int, object] | None, decision: str) -> bool:
    return result is not None and result[0] == 200 and isinstance(result[1], dict) and result[1].get("decision") == decision


def view(lists: dict | None) -> dict:
    """What the screen shows; every key is present even without the channel, so the screen never binds to an undefined text."""
    if lists is None:
        return {"available": False, "pending": [], "decided": [], "none": False}
    pending = [
        dict(p, meta=_("OPSPROP_META", id=p["incidentId"], node=p["sourceNode"], severity=p["severity"], at=p["detectedAt"]), title=p["component"] or p["incidentId"])
        for p in lists["pending"]
    ]
    decided = [
        _("OPSPROP_DECIDED_APPROVED" if d["decision"] == "approved" else "OPSPROP_DECIDED_REJECTED", id=d["incidentId"], by=d["by"], at=d["decidedAt"])
        for d in reversed(lists["decided"][-5:])
    ]
    return {"available": True, "pending": pending, "decided": decided, "none": not pending}
