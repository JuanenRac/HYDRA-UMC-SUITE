# =============================================================================
# HYDRA-UMC SUITE - panel_logic/service_identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The identity the server presents to the services it calls (GET /api/admin/service-identity, and the switch auth.serviceIdentity.enabled of
# PUT /api/admin/server-config, OFF by default). Giving each service the key to verify that token is done by the operator of the machine
# (provisioning/service_identity.py of HYDRA-UMC-OS, as root); this app only shows the state and changes the switch of the server. Read
# without any window toolkit; a server without the route (404) and an account that may not use it (401/403) are told apart from a failure.
# =============================================================================
from __future__ import annotations

from hydra_suite.i18n import _

SUPPORTS = ("accepts", "own_verifier", "not_yet")
STATES = ("presenting", "idle_no_key", "off")
SOURCES = ("env", "config", "default")


def parse_status(body: object) -> dict | None:
    """The status in an answer of the route; None when the answer does not have the shape. An unknown support level is dropped, never guessed."""
    if not isinstance(body, dict):
        return None
    if not isinstance(body.get("enabled"), bool) or body.get("source") not in SOURCES or body.get("state") not in STATES:
        return None
    services = []
    for item in body.get("services") if isinstance(body.get("services"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"] and item.get("support") in SUPPORTS:
            services.append({"name": item["name"], "support": item["support"]})
    return {
        "enabled": body["enabled"],
        "locked": body.get("locked") is True,
        "state": body["state"],
        "services": services,
    }


def body_for(enabled: bool) -> dict:
    """The body of the change. Turning the switch on carries confirm: true; turning it off never does."""
    return {"auth": {"serviceIdentity": {"enabled": True, "confirm": True} if enabled else {"enabled": False}}}


def needs_confirmation(current: bool, wanted: bool) -> bool:
    return bool(wanted and not current)


def change_allowed(status: dict, wanted: bool) -> bool:
    """The environment of the server can lock the switch; then no change is offered."""
    return wanted == status["enabled"] or not status["locked"]


def hidden_for(result: tuple[int, object] | None) -> bool:
    """True when the server has no such route: the section stays out of the way."""
    return result is not None and result[0] == 404


def status_for(result: tuple[int, object] | None) -> str:
    """The sentence for a failed reading or change, empty when it worked."""
    if result is None:
        return _("SERVICEID_LOAD_ERROR")
    status, body = result
    if status in (401, 403):
        return _("SERVICEID_FORBIDDEN")
    if status == 200 and (parse_status(body) is not None or (isinstance(body, dict) and body.get("success") is True)):
        return ""
    detail = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else ""
    if status >= 300 and detail:
        return _("SERVICEID_SAVE_ERROR", reason=detail[:300])
    return _("SERVICEID_LOAD_ERROR")


def _line(status: dict, support: str, key: str) -> str:
    names = [s["name"] for s in status["services"] if s["support"] == support]
    return f"{_(key)} ({len(names)}): {', '.join(names) if names else _('SERVICEID_NONE')}"


def view(status: dict | None) -> dict:
    """What the screen shows."""
    if status is None:
        return {"available": False}
    return {
        "available": True,
        "enabled": status["enabled"],
        "locked": status["locked"],
        "state": _("SERVICEID_STATE_" + status["state"].upper()),
        "lockedText": _("SERVICEID_LOCKED") if status["locked"] else "",
        "accepts": _line(status, "accepts", "SERVICEID_ACCEPTS"),
        "ownVerifier": _line(status, "own_verifier", "SERVICEID_OWN_VERIFIER"),
        "notYet": _line(status, "not_yet", "SERVICEID_NOT_YET"),
        "servicesTitle": _("SERVICEID_SERVICES_TITLE"),
        "orderTitle": _("SERVICEID_ORDER_TITLE"),
        "order1": _("SERVICEID_ORDER_1"),
        "order2": _("SERVICEID_ORDER_2"),
        "order3": _("SERVICEID_ORDER_3"),
        "offWarning": _("SERVICEID_OFF_WARNING"),
    }
